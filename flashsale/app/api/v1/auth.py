from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import (
    create_access_token,
    store_token,
    revoke_token,
    revoke_all_tokens,
    verify_password,
    JWTBearer
)
from app.services.user_service import get_user_by_username, create_user, add_favorite_product, remove_favorite_product, get_favorite_products, get_user
from app.schemas.user import User, UserCreate, UserRegister, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User, summary="注册新用户")
async def register(
    user_register: UserRegister,
    db: Session = Depends(get_db)
):
    """
    注册新用户接口

    请求体:
    - username: 用户名（唯一）
    - password: 密码
    - name: 用户姓名
    - age: 用户年龄

    返回:
    - user: 创建的用户信息
    """
    existing_user = get_user_by_username(db, user_register.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    user_create = UserCreate(
        username=user_register.username,
        password=user_register.password,
        name=user_register.name,
        age=user_register.age
    )
    user = create_user(db, user_create)
    return user

@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录接口

    请求体:
    - username: 用户名
    - password: 密码

    返回:
    - access_token: JWT访问令牌
    - token_type: 令牌类型（bearer）
    - user: 用户信息
    """
    user = get_user_by_username(db, login_request.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    access_token = create_access_token(data={"sub": user.id})

    store_token(access_token, user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    用户登出接口

    请求头:
    - Authorization: Bearer <token>

    返回:
    - message: 登出成功消息
    """
    auth = request.headers.get("Authorization")
    scheme, token = auth.split() if auth else (None, None)
    
    if token:
        revoke_token(token, user_id)
    
    return {"message": "登出成功"}
#post表示提交数据，提交给服务器处理
@router.post("/logout-all", summary="登出所有设备")
async def logout_all(
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    登出所有设备接口

    请求头:
    - Authorization: Bearer <token>

    返回:
    - message: 操作成功消息
    """
    revoke_all_tokens(user_id)

    return {"message": "已登出所有设备"}
#get表示获取数据，不提交数据
@router.get("/me", response_model=User, summary="获取当前用户信息")
async def get_current_user(
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    获取当前用户信息接口

    请求头:
    - Authorization: Bearer <token>

    返回:
    - user: 用户信息
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.post("/favorite/{product_id}", response_model=User, summary="添加喜欢的商品")
async def add_favorite(
    product_id: int,
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    添加喜欢的商品接口

    请求头:
    - Authorization: Bearer <token>

    参数:
    - product_id: 商品ID

    返回:
    - user: 更新后的用户信息
    """
    user = add_favorite_product(db, user_id, product_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.delete("/favorite/{product_id}", summary="取消收藏")
async def remove_favorite(
    product_id: int,
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    取消收藏商品接口

    请求头:
    - Authorization: Bearer <token>

    参数:
    - product_id: 商品ID

    返回:
    - message: 操作成功消息
    """
    user = remove_favorite_product(db, user_id, product_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return {"message": "取消收藏成功"}

@router.get("/favorite", summary="获取喜欢的商品列表")
async def get_favorites(
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    获取喜欢的商品列表接口

    请求头:
    - Authorization: Bearer <token>

    返回:
    - favorites: 商品ID列表
    """
    favorites = get_favorite_products(db, user_id)
    return {"favorites": favorites}