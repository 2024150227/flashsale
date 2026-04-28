from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

from app.api.v1 import products, orders
from app.core.config import settings

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

app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])

static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
print(f"[DEBUG] Static files path: {static_path}")
print(f"[DEBUG] Path exists: {os.path.exists(static_path)}")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    print("[DEBUG] Static files mounted successfully")

@app.get('/')
async def root():
    html_path = os.path.join(static_path, 'index.html')
    print(f"[DEBUG] Serving HTML from: {html_path}")
    print(f"[DEBUG] HTML exists: {os.path.exists(html_path)}")
    return FileResponse(html_path)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
