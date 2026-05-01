from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "FlashSale"
    app_version: str = "1.0.0"
    # 是否开启调试模式
    debug: bool = True
    
    # 数据库配置
    database_url: str = "mysql+pymysql://root:123456@mysql:3306/flashsale"
    
       # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    
    # Kafka配置
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "flashsale_orders"
    
    # 限流配置
    rate_limit: str = "1000/minute"
    
    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()