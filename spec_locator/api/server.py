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
import hashlib
import time
from typing import Optional
from contextlib import asynccontextmanager
from threading import Thread
import cv2
import numpy as np
import fitz  # PyMuPDF

try:
    from fastapi import FastAPI, File, UploadFile, HTTPException, Query  # 添加Query
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")

from spec_locator.config import APIConfig, ErrorCode, ERROR_MESSAGES, PathConfig, LOG_LEVEL, OCRConfig, LLMConfig  # 添加LLMConfig
from spec_locator.core import SpecLocatorPipeline

logger = logging.getLogger(__name__)

# 全局变量：延迟初始化
pipeline = None

# PDF预览缓存目录
PREVIEW_CACHE_DIR = os.path.join(PathConfig.TEMP_DIR, "pdf_previews")
PREVIEW_CACHE_MAX_AGE = 3600  # 缓存1小时

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
    
    # 创建PDF预览缓存目录
    os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)
    logger.info(f"PDF预览缓存目录: {PREVIEW_CACHE_DIR}")
    
    # 验证数据目录
    try:
        PathConfig.validate_data_dir()
        logger.info(f"数据目录: {PathConfig.SPEC_DATA_DIR}")
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.warning(str(e))
        logger.warning("数据目录不可用，文件查找功能将受限")
    
    # 初始化 Pipeline（懒加载模式，支持LLM）
    # 如果LLM已启用且配置正确，初始化为auto模式以支持LLM调用
    initial_method = "auto" if (LLMConfig.ENABLED and LLMConfig.validate()) else "ocr"
    pipeline = SpecLocatorPipeline(
        lazy_ocr=OCRConfig.LAZY_LOAD,
        recognition_method=initial_method
    )
    logger.info(f"✓ Pipeline 初始化完成（OCR 懒加载: {OCRConfig.LAZY_LOAD}, 识别方式: {initial_method}）")
    
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

# 挂载静态文件目录
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"✓ 静态文件目录已挂载: {static_path}")
else:
    logger.warning(f"静态文件目录不存在: {static_path}")

@app.get("/")
async def read_root():
    """返回首页"""
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Spec Locator Service API", "docs": "/docs"}

@app.get("/demo")
async def read_demo():
    """返回演示页面"""
    demo_file = os.path.join(static_path, "index.html")
    if os.path.exists(demo_file):
        return FileResponse(demo_file)
    return JSONResponse(
        status_code=404,
        content={"message": "Demo page not found. Please deploy static files."}
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
        "llm_enabled": LLMConfig.ENABLED,  # 显示LLM是否启用
        "llm_configured": LLMConfig.validate(),  # 显示LLM是否正确配置
    }


@app.post("/api/spec-locate")
async def locate_spec(
    file: UploadFile = File(...),
    method: str = Query(
        default="ocr",
        pattern="^(ocr|llm|auto)$",
        description="识别方式: ocr-OCR识别, llm-大模型识别, auto-智能切换"
    )
):
    """
    规范定位识别接口（支持多种识别方式）

    接收一张 CAD 截图，返回识别到的规范编号和页码

    Args:
        file: CAD 截图文件
        method: 识别方式 (ocr/llm/auto)

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

        # 3. 根据method参数设置识别方式
        original_method = pipeline.recognition_method
        pipeline.recognition_method = method
        
        # 4. 调用流水线处理
        logger.info(f"Processing file: {filename} with method: {method}")
        result = pipeline.process(image)
        
        # 恢复原始设置
        pipeline.recognition_method = original_method

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


@app.get("/api/pdf-page-preview")
async def pdf_page_preview(
    spec_code: str = Query(..., description="规范编号，如 12J2"),
    page_code: str = Query(None, description="页码编号，如 C11, 1-11（推荐使用，确保与下载功能一致）"),
    page_number: int = Query(default=1, ge=1, description="PDF内部页码，从1开始，默认第1页"),
    dpi: int = Query(default=150, ge=72, le=300, description="图片DPI质量，默认150")
):
    """
    PDF页面预览接口 - 将指定PDF页面转换为图片
    
    支持两种调用方式：
    1. 新方式（推荐）：提供 page_code，使用与下载功能相同的精确查找
    2. 旧方式（兼容）：不提供 page_code，使用规范下的第一个文件
    
    Args:
        spec_code: 规范编号（如 12J2）
        page_code: 页码编号（如 C11, 1-11），用于定位具体的PDF文件（可选，推荐提供）
        page_number: PDF内部页码（从1开始），用于定位文件内的具体页面，默认为1
        dpi: 图片质量，默认150 DPI

    Returns:
        图片文件
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="服务正在初始化中，请稍后重试")
    
    try:
        # 1. 查找PDF文件
        pdf_file = None
        
        if page_code:
            # 新方式：使用与下载功能相同的精确查找逻辑
            pdf_file = pipeline.file_index.find_file(spec_code, page_code)
            
            if not pdf_file:
                return JSONResponse(
                    status_code=404,
                    content={
                        "success": False,
                        "error_code": "FILE_NOT_FOUND",
                        "message": f"未找到 {spec_code} 页码 {page_code} 对应的PDF文件",
                        "hint": "请检查规范编号和页码是否正确"
                    }
                )
        else:
            # 旧方式（向后兼容）：使用规范下的第一个文件
            logger.warning(f"使用旧API格式（无page_code参数）: spec_code={spec_code}, page_number={page_number}")
            logger.warning(f"建议更新前端代码以提供page_code参数，确保与下载功能一致")
            
            spec_files = pipeline.file_index.get_spec_files(spec_code)
            
            if not spec_files:
                return JSONResponse(
                    status_code=404,
                    content={
                        "success": False,
                        "error_code": "SPEC_NOT_FOUND",
                        "message": f"规范 {spec_code} 不存在",
                        "hint": "建议提供page_code参数以精确定位PDF文件"
                    }
                )
            
            pdf_file = spec_files[0]
            logger.info(f"向后兼容模式：使用第一个文件 {pdf_file.file_name}")
        
        # 检查文件是否存在
        if not pdf_file or not os.path.exists(pdf_file.file_path):
            logger.error(f"File not found on disk: {pdf_file.file_path if pdf_file else 'None'}")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error_code": "FILE_NOT_FOUND",
                    "message": "文件在服务器上不存在",
                }
            )
        
        pdf_path = pdf_file.file_path
        
        # 2. 检查缓存
        cache_key = f"{spec_code}_{page_code or 'default'}_{page_number}_{dpi}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        cache_file = os.path.join(PREVIEW_CACHE_DIR, f"{cache_hash}.png")
        
        # 如果缓存存在且未过期，直接返回
        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            if cache_age < PREVIEW_CACHE_MAX_AGE:
                logger.info(f"使用缓存: {cache_key}")
                return FileResponse(
                    path=cache_file,
                    media_type="image/png",
                    headers={"Cache-Control": f"public, max-age={PREVIEW_CACHE_MAX_AGE}"}
                )
        
        # 3. 转换PDF页面为图片
        logger.info(f"转换PDF页面: {spec_code} {page_code or '(第一个文件)'} 第{page_number}页 (文件: {pdf_file.file_name}, DPI: {dpi})")
        
        try:
            doc = fitz.open(pdf_path)
            
            # 检查页码是否有效
            if page_number < 1 or page_number > len(doc):
                doc.close()
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error_code": "INVALID_PAGE_NUMBER",
                        "message": f"页码超出范围，PDF共有 {len(doc)} 页",
                        "total_pages": len(doc)
                    }
                )
            
            # 获取指定页面（索引从0开始）
            page = doc.load_page(page_number - 1)
            
            # 设置缩放比例（DPI转换为缩放因子）
            zoom = dpi / 72  # 72是PDF的默认DPI
            mat = fitz.Matrix(zoom, zoom)
            
            # 渲染为图片
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # 保存到缓存
            pix.save(cache_file)
            
            doc.close()
            
            logger.info(f"PDF页面转换成功: {cache_file}")
            
            # 返回图片
            return FileResponse(
                path=cache_file,
                media_type="image/png",
                headers={"Cache-Control": f"public, max-age={PREVIEW_CACHE_MAX_AGE}"}
            )
            
        except Exception as e:
            logger.error(f"PDF转换失败: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error_code": "CONVERSION_ERROR",
                    "message": f"PDF转换失败: {str(e)}",
                }
            )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"预览错误: {e}", exc_info=True)
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
