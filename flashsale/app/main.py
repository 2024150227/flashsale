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
from app.core.config import settings
from app.core.logger import main_logger as logger
        
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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])

# 静态文件服务
static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
logger.debug(f"Static files path: {static_path}")
logger.debug(f"Path exists: {os.path.exists(static_path)}")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info("Static files mounted successfully")

# 默认路由重定向到登录页面
@app.get('/')
async def root():
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

# 健康检查路由
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
