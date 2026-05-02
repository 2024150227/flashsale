from fastapi import APIRouter, HTTPException, Request, Depends, Query
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional, List

from app.schemas.order import OrderCreate, OrderResponse, OrderDetail, OrderListResponse
from app.services.order_service import OrderService
from app.core.logger import orders_api_logger as logger
from app.core.security import JWTBearer
from app.db.session import SessionLocal
from app.models.order import Order

router = APIRouter()
order_service = OrderService()

# 对下单接口进行限流
limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=OrderResponse)
@limiter.limit("5000/second")  # 放宽到每秒5000次，适应秒杀场景
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

@router.get("/", response_model=OrderListResponse)
async def get_orders(
    user_id: int = Depends(JWTBearer()),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    查询当前用户的订单列表

    需要JWT认证

    参数:
    - limit: 返回数量，默认20，最大100
    - offset: 偏移量，默认0

    返回:
    - total: 总数
    - orders: 订单列表
    """
    db = SessionLocal()
    try:
        total = db.query(Order).filter(Order.user_id == user_id).count()
        orders = db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(
            Order.created_at.desc()
        ).offset(offset).limit(limit).all()

        return OrderListResponse(
            total=total,
            orders=[OrderDetail.model_validate(o) for o in orders]
        )
    finally:
        db.close()

@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: int,
    user_id: int = Depends(JWTBearer())
):
    """
    查询指定订单详情

    需要JWT认证，只能查看自己的订单
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        return OrderDetail.model_validate(order)
    finally:
        db.close()

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    user_id: int = Depends(JWTBearer())
):
    """
    取消订单

    需要JWT认证，只能取消自己的订单
    条件：下单时间不超过24小时
    """
    from datetime import datetime, timedelta
    from app.utils.redis_client import redis_client

    db = SessionLocal()
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        if order.status == "cancelled":
            raise HTTPException(status_code=400, detail="订单已取消")

        if order.status == "refunded":
            raise HTTPException(status_code=400, detail="订单已退款")

        time_elapsed = datetime.now() - order.created_at
        if time_elapsed > timedelta(hours=24):
            raise HTTPException(status_code=400, detail="订单超过24小时，无法取消")

        order.status = "cancelled"
        db.commit()

        stock_key = f"flashsale:stock:{order.product_id}"
        redis_client.incr(stock_key)

        return {"message": "订单已取消", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()