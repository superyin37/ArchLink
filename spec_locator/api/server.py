"""
HTTP API 服务层
- 提供 HTTP 接口
- 处理文件上传与参数校验
- 调用内部识别流水线
- 统一封装返回结果与错误码
"""

import logging
import os
import tempfile
from typing import Optional
from contextlib import asynccontextmanager
from threading import Thread
import cv2
import numpy as np

try:
    from fastapi import FastAPI, File, UploadFile, HTTPException
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")

from spec_locator.config import APIConfig, ErrorCode, ERROR_MESSAGES, PathConfig, LOG_LEVEL, OCRConfig
from spec_locator.core import SpecLocatorPipeline

logger = logging.getLogger(__name__)

# 全局变量：延迟初始化
pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - startup: 初始化Pipeline，可选后台预热OCR
    - shutdown: 清理资源
    """
    # 启动时
    global pipeline
    logger.info("Spec Locator Service 启动中...")
    
    # 确保必要目录存在
    PathConfig.ensure_dirs()
    
    # 验证数据目录
    try:
        PathConfig.validate_data_dir()
        logger.info(f"数据目录: {PathConfig.SPEC_DATA_DIR}")
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.warning(str(e))
        logger.warning("数据目录不可用，文件查找功能将受限")
    
    # 初始化 Pipeline（懒加载模式）
    pipeline = SpecLocatorPipeline(lazy_ocr=OCRConfig.LAZY_LOAD)
    logger.info(f"✓ Pipeline 初始化完成（OCR 懒加载: {OCRConfig.LAZY_LOAD}）")
    
    # 可选：后台异步预热 OCR（不阻塞启动）
    if OCRConfig.WARMUP_ON_STARTUP:
        def warmup_in_background():
            try:
                logger.info("后台预热 OCR 模型...")
                pipeline.warmup()
                logger.info("✓ OCR 模型预热完成")
            except Exception as e:
                logger.error(f"OCR 预热失败: {e}")
        
        # 在后台线程中预热
        warmup_thread = Thread(target=warmup_in_background, daemon=True)
        warmup_thread.start()
    
    logger.info("✓ Spec Locator Service 启动完成")
    
    yield  # 应用运行中
    
    # 关闭时
    logger.info("Spec Locator Service 关闭中...")
    logger.info("✓ Spec Locator Service 已关闭")

# 初始化 FastAPI 应用
app = FastAPI(
    title="Spec Locator Service",
    description="CAD 规范定位识别服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """健康检查端点"""
    if pipeline is None:
        return {
            "status": "initializing",
            "message": "服务正在初始化中"
        }
    
    stats = pipeline.file_index.get_stats()
    return {
        "status": "ok",
        "index_stats": stats,
        "ocr_loaded": pipeline.ocr_engine._initialized,  # 显示OCR是否已加载
    }


@app.post("/api/spec-locate")
async def locate_spec(file: UploadFile = File(...)):
    """
    规范定位识别接口（会触发OCR懒加载）

    接收一张 CAD 截图，返回识别到的规范编号和页码

    Args:
        file: CAD 截图文件

    Returns:
        JSON 响应
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="服务正在初始化中，请稍后重试")
    
    try:
        # 1. 文件验证
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        # 检查文件扩展名
        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in APIConfig.ALLOWED_EXTENSIONS):
            return _error_response(ErrorCode.INVALID_FILE)

        # 检查文件大小
        contents = await file.read()
        if len(contents) > APIConfig.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large")

        # 2. 读取图像
        try:
            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return _error_response(ErrorCode.INVALID_FILE)
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return _error_response(ErrorCode.INVALID_FILE)

        # 3. 调用流水线处理
        logger.info(f"Processing file: {filename}")
        result = pipeline.process(image)

        return JSONResponse(content=result)

    except HTTPException as e:
        logger.error(f"HTTP exception: {e}")
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "error_code": "INVALID_REQUEST",
                "message": e.detail,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _error_response(ErrorCode.INTERNAL_ERROR)


@app.get("/api/download/{spec_code}/{page_code}")
def download_pdf(spec_code: str, page_code: str):
    """
    下载PDF文件端点

    Args:
        spec_code: 规范编号（如 12J2）
        page_code: 页码（如 C11）

    Returns:
        PDF文件
    """
    try:
        # 查找文件
        pdf_file = pipeline.file_index.find_file(spec_code, page_code)
        
        if not pdf_file:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error_code": "FILE_NOT_FOUND",
                    "message": f"PDF file not found for {spec_code} page {page_code}",
                },
            )

        # 检查文件是否存在
        if not os.path.exists(pdf_file.file_path):
            logger.error(f"File not found on disk: {pdf_file.file_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error_code": "FILE_NOT_FOUND",
                    "message": "File not found on server",
                },
            )

        # 返回文件
        return FileResponse(
            path=pdf_file.file_path,
            filename=pdf_file.file_name,
            media_type="application/pdf",
        )

    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


def _error_response(error_code: ErrorCode):
    """生成标准错误响应"""
    return JSONResponse(
        status_code=200,  # 保持 200 OK，错误信息在 body 中
        content={
            "success": False,
            "error_code": error_code.value,
            "message": ERROR_MESSAGES.get(error_code, "Unknown error"),
        },
    )


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "Internal server error",
        },
    )


def run_server(
    host: str = APIConfig.HOST,
    port: int = APIConfig.PORT,
    workers: int = APIConfig.WORKERS,
):
    """运行服务器"""
    import uvicorn

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_server()
