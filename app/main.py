from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import threading

from app.api.v1 import products, orders
from app.api.v1.auth import router as auth_router
from app.api.v1.cache import router as cache_router
from app.core.config import settings
from app.core.logger import main_logger as logger
from app.middleware.bloom_filter import bloom_filter_middleware
from app.services.cache_warmup import warmup_products_cache

# Kafka消费者相关
from app.utils.kafka_service import kafka_service
from app.utils.kafka_consumer_manager import kafka_consumer_manager
from app.services.order_service import OrderService

order_service = OrderService()

def process_order_message(message: dict):
    """处理单个订单消息"""
    logger.info(f"[ORDER] Processing order: {message}")
    order_service.process_order(message)

# 启动多个Kafka消费者（默认3个消费者实例）
try:
    kafka_consumer_manager.start_consumers(
        topic=settings.kafka_topic_orders,
        callback=process_order_message,
        num_consumers=3,
        group_id='flashsale-orders-group'
    )
    logger.info("Multiple Kafka consumers started successfully")
except Exception as e:
    logger.error(f"Failed to start Kafka consumers: {e}")

# 执行 Redis 缓存预热
try:
    warmup_products_cache()
except Exception as e:
    logger.error(f"Redis 缓存预热失败: {e}")
        
app = FastAPI(
    title="FlashSale API",
    description="高并发秒杀系统 API",
    version="1.0.0"
)
# 配置CORS中间件 - 允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# 注册布隆过滤器中间件 - 拦截恶意查询
app.middleware("http")(bloom_filter_middleware)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(cache_router, prefix="/api/v1", tags=["cache"])

# 静态文件服务
static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
logger.debug(f"Static files path: {static_path}")
logger.debug(f"Path exists: {os.path.exists(static_path)}")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info("Static files mounted successfully")
    
    # 头像目录静态文件服务
    avatar_path = os.path.join(static_path, "avatars")
    if os.path.exists(avatar_path):
        app.mount("/avatars", StaticFiles(directory=avatar_path), name="avatars")
        logger.info("Avatars static files mounted successfully")

# 默认路由重定向到登录页面
@app.get('/')
async def root():
    html_path = os.path.join(static_path, 'login.html')
    logger.debug(f"Serving login HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

# 登录页面路由
@app.get('/login')
async def login():
    html_path = os.path.join(static_path, 'login.html')
    logger.debug(f"Serving login HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

# 秒杀页面路由
@app.get('/flashsale')
async def flashsale():
    html_path = os.path.join(static_path, 'index.html')
    logger.debug(f"Serving flashsale HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

# 客服页面路由
@app.get('/chat.html')
async def chat():
    html_path = os.path.join(static_path, 'chat.html')
    logger.debug(f"Serving chat HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

# 健康检查路由
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
