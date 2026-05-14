from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "FlashSale"
    app_version: str = "1.0.0"
    # 是否开启调试模式
    debug: bool = True
    
    # 数据库配置 - 默认（兼容旧代码）
    database_url: str = "mysql+mysqlconnector://root:mysql123456@mysql-master:3306/flashsale"
    
    # 数据库配置 - 主库（写操作）
    database_url_master: str = "mysql+mysqlconnector://root:mysql123456@mysql-master:3306/flashsale"
    
    # 数据库配置 - 从库（读操作）
    database_url_slave: str = "mysql+mysqlconnector://root:mysql123456@mysql-slave:3306/flashsale"
    
    # Redis配置，用于缓存用户token和订单
    redis_url: str = "redis://redis:6379/0"
    
    # Kafka配置,bootstrap_servers的翻译是引导服务器
    kafka_bootstrap_servers: str = 'kafka:9092'
    kafka_topic: Optional[str] = None  # 兼容旧环境变量配置
    
    # Kafka生产者配置
    kafka_producers_per_topic: int = 3  # 每个Topic的生产者数量
    kafka_acks: str = 'all'  # 消息确认模式
    kafka_compression_type: str = 'lz4'  # 压缩类型
    kafka_batch_size: int = 16384  # 批量发送阈值(字节)
    kafka_linger_ms: int = 5  # 等待批量发送时间(毫秒)
    
    # 订单Topic - 秒杀订单异步处理
    kafka_topic_orders: str = 'flashsale_orders'
    
    # 支付Topic - 订单支付回调处理
    kafka_topic_payments: str = 'flashsale_payments'
    
    # 通知Topic - 用户通知消息
    kafka_topic_notifications: str = 'flashsale_notifications'
    
    # 日志Topic - 操作日志记录
    kafka_topic_logs: str = 'flashsale_logs'
    
    # 限流配置，每个秒最多处理5000条订单
    rate_limit: str = "5000/second"
    
    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()