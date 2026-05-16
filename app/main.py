from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

from app.api.v1 import products, orders
from app.api.v1.auth import router as auth_router
from app.api.v1.cache import router as cache_router
from app.core.config import settings
from app.core.logger import main_logger as logger
from app.middleware.bloom_filter import bloom_filter_middleware
from app.middleware.high_concurrency import (
    RateLimitMiddleware,
    CircuitBreakerMiddleware,
    AntiSpamMiddleware,
    DegradationMiddleware
)
from app.services.cache_warmup import warmup_products_cache
from app.utils.local_cache import local_cache

from app.utils.kafka_service import kafka_service
from app.utils.kafka_consumer_manager import kafka_consumer_manager
from app.services.order_service import OrderService

order_service = OrderService()

def process_order_message(message: dict):
    logger.info(f"[ORDER] Processing order: {message}")
    order_service.process_order(message)

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

try:
    warmup_products_cache()
except Exception as e:
    logger.error(f"Redis cache warmup failed: {e}")

logger.info("Local cache initialized")

app = FastAPI(
    title="FlashSale API",
    description="高并发秒杀系统 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.add_middleware(RateLimitMiddleware, max_requests=1000, window_seconds=60)
logger.info("RateLimitMiddleware registered")

app.add_middleware(CircuitBreakerMiddleware, failure_threshold=50, recovery_timeout=60)
logger.info("CircuitBreakerMiddleware registered")

app.add_middleware(AntiSpamMiddleware)
logger.info("AntiSpamMiddleware registered")

app.add_middleware(DegradationMiddleware)
logger.info("DegradationMiddleware registered")

app.middleware("http")(bloom_filter_middleware)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(cache_router, prefix="/api/v1", tags=["cache"])

static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
logger.debug(f"Static files path: {static_path}")
logger.debug(f"Path exists: {os.path.exists(static_path)}")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info("Static files mounted successfully")
    
    avatar_path = os.path.join(static_path, "avatars")
    if os.path.exists(avatar_path):
        app.mount("/avatars", StaticFiles(directory=avatar_path), name="avatars")
        logger.info("Avatars static files mounted successfully")

@app.get('/')
async def root():
    html_path = os.path.join(static_path, 'login.html')
    logger.debug(f"Serving login HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

@app.get('/login')
async def login():
    html_path = os.path.join(static_path, 'login.html')
    logger.debug(f"Serving login HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

@app.get('/flashsale')
async def flashsale():
    html_path = os.path.join(static_path, 'index.html')
    logger.debug(f"Serving flashsale HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

@app.get('/chat.html')
async def chat():
    html_path = os.path.join(static_path, 'chat.html')
    logger.debug(f"Serving chat HTML from: {html_path}")
    logger.debug(f"HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}