from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService

router = APIRouter()
order_service = OrderService()

# 对下单接口进行限流
limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=OrderResponse)
@limiter.limit("1000/minute")
async def create_order(request: Request, order: OrderCreate):
    """创建秒杀订单"""
    try:
        result = order_service.create_order(order.user_id, order.product_id)
        return OrderResponse(status="queued", message="订单已进入处理队列")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))