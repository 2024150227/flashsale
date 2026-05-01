import logging
import os
from datetime import datetime
from typing import Optional

def setup_root_logger():
    """配置根日志器"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger("flashsale")
    root_logger.setLevel(logging.DEBUG)
    root_logger.propagate = False

    if root_logger.handlers:
        return root_logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(console_handler)
    return root_logger

def get_logger(module_name: str, log_to_file: bool = True) -> logging.Logger:
    """获取模块级别的日志器"""
    setup_root_logger()

    logger = logging.getLogger(f"flashsale.{module_name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_to_file:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{date_str}_{module_name.replace('.', '_')}.log"
        log_path = os.path.join(log_dir, log_filename)

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 预定义常用模块的logger（只保留子模块，避免重复）
products_api_logger = get_logger("api.products")
orders_api_logger = get_logger("api.orders")
product_service_logger = get_logger("service.product")
order_service_logger = get_logger("service.order")
db_logger = get_logger("db")
config_logger = get_logger("config")
main_logger = get_logger("main")