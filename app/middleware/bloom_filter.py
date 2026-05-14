from fastapi import Request, HTTPException
from fastapi.routing import Match
from app.utils.bloom_filter import is_product_exists, is_user_exists
from typing import Optional

async def bloom_filter_middleware(request: Request, call_next):
    """
    布隆过滤器中间件 - 拦截恶意查询
    
    功能：
    1. 拦截查询不存在商品的请求
    2. 拦截非法用户请求
    3. 减少无效请求对后端的压力
    """
    
    # 获取请求路径和方法
    path = request.url.path
    method = request.method
    
    # 跳过健康检查和静态资源
    if path.startswith("/health") or path.startswith("/static"):
        return await call_next(request)
    
    try:
        # 解析路径参数
        product_id: Optional[int] = None
        user_id: Optional[int] = None
        
        # 获取路由匹配信息
        for route in request.app.routes:
            match, _ = route.matches(request)
            if match == Match.FULL:
                # 获取路径参数
                path_params = route.path_params
                if 'product_id' in path_params:
                    product_id = request.path_params.get('product_id')
                if 'user_id' in path_params:
                    user_id = request.path_params.get('user_id')
                break
        
        # 检查请求体中的参数（POST请求）
        if method == "POST":
            try:
                body = await request.json()
                if 'product_id' in body:
                    product_id = body['product_id']
                if 'user_id' in body:
                    user_id = body['user_id']
            except:
                pass
        
        # 检查商品ID（秒杀相关接口）
        if product_id and path.startswith("/api/v1/products"):
            if not is_product_exists(product_id):
                raise HTTPException(
                    status_code=404,
                    detail=f"商品不存在: {product_id}"
                )
        
        # 检查用户ID（订单相关接口）
        if user_id and path.startswith("/api/v1/orders"):
            if not is_user_exists(user_id):
                raise HTTPException(
                    status_code=401,
                    detail=f"用户不存在: {user_id}"
                )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        # 布隆过滤器检查失败时，继续处理请求（降级）
        pass
    
    # 继续处理请求
    response = await call_next(request)
    return response
