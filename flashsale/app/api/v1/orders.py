from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService
from app.core.logger import orders_api_logger as logger
from app.core.security import JWTBearer

router = APIRouter()
order_service = OrderService()

# 对下单接口进行限流
limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=OrderResponse)
@limiter.limit("50000/minute")  # 放宽到每分钟50000次，适应秒杀场景
async def create_order(
    request: Request, 
    order: OrderCreate,
    user_id: int = Depends(JWTBearer())
):
    """
    创建秒杀订单
    
    需要JWT认证，只有登录用户才能下单
    
    请求头:
    - Authorization: Bearer <token>
    
    请求体:
    - user_id: 用户ID（可选，会被token中的用户ID覆盖）
    - product_id: 商品ID
    
    返回:
    - status: 订单状态
    - message: 提示信息
    """
    try:
        # 使用token中的用户ID，忽略请求体中的user_id
        result = order_service.create_order(user_id, order.product_id)
        return OrderResponse(status="queued", message="订单已进入处理队列")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))