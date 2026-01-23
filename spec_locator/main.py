"""
Spec Locator Service - 主程序入口

使用方法：
    python main.py  # 启动 HTTP 服务
"""

import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spec_locator.config import PathConfig, APIConfig
from spec_locator.api.server import run_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(PathConfig.LOG_DIR, "app.log")),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """主程序入口"""
    logger.info("=" * 60)
    logger.info("Spec Locator Service v1.0")
    logger.info("=" * 60)

    # 初始化必要的目录
    PathConfig.ensure_dirs()
    logger.info(f"Project root: {PathConfig.PROJECT_ROOT}")

    # 启动 HTTP 服务
    logger.info(f"Starting server on {APIConfig.HOST}:{APIConfig.PORT}")
    run_server(
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        workers=APIConfig.WORKERS,
    )


if __name__ == "__main__":
    main()
