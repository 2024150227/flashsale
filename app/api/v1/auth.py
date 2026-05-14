from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import shutil

from app.db.session import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    store_tokens,
    revoke_access_token,
    revoke_refresh_token,
    revoke_all_tokens,
    verify_password,
    JWTBearer,
    RefreshTokenBearer
)
from app.services.user_service import get_user_by_username, create_user, add_favorite_product, remove_favorite_product, get_favorite_products, get_user, update_user_avatar
from app.schemas.user import User, UserCreate, UserRegister, LoginRequest, LoginResponse, RefreshResponse

# 头像存储目录
AVATAR_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'avatars')
os.makedirs(AVATAR_DIR, exist_ok=True)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User, summary="注册新用户")
async def register(
    user_register: UserRegister,
    db: Session = Depends(get_db)
):
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
        age=user_register.age,
        avatar=user_register.avatar or "👤"
    )
    user = create_user(db, user_create)
    return user

@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
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
    refresh_token = create_refresh_token(data={"sub": user.id})

    store_tokens(access_token, refresh_token, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/refresh", response_model=RefreshResponse, summary="刷新Access Token")
async def refresh_token(
    request: Request,
    user_id: int = Depends(RefreshTokenBearer()),
    db: Session = Depends(get_db)
):
    auth = request.headers.get("Authorization")
    parts = auth.split()
    old_refresh_token = parts[1] if len(parts) == 2 else None

    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    new_access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    if old_refresh_token:
        revoke_refresh_token(old_refresh_token, user_id)

    store_tokens(new_access_token, new_refresh_token, user.id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    auth = request.headers.get("Authorization")
    scheme, token = auth.split() if auth else (None, None)

    if token:
        revoke_access_token(token, user_id)

    return {"message": "登出成功"}

@router.post("/logout-all", summary="登出所有设备")
async def logout_all(
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    revoke_all_tokens(user_id)

    return {"message": "已登出所有设备"}

@router.get("/me", response_model=User, summary="获取当前用户信息")
async def get_current_user(
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
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
    favorites = get_favorite_products(db, user_id)
    return {"favorites": favorites}

@router.post("/avatar", response_model=User, summary="上传/更新头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    上传用户头像图片
    
    支持的格式: jpg, jpeg, png, gif, webp
    最大文件大小: 5MB
    """
    # 检查文件类型
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    file_extension = file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的图片格式，请上传 jpg、png、gif 或 webp 格式")
    
    # 检查文件大小 (5MB)
    file_size = 0
    while chunk := await file.read(1024):
        file_size += len(chunk)
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")
    
    # 重置文件指针
    await file.seek(0)
    
    # 生成文件名
    filename = f"avatar_{user_id}.{file_extension}"
    file_path = os.path.join(AVATAR_DIR, filename)
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 更新用户头像路径
    avatar_path = f"/avatars/{filename}"
    user = update_user_avatar(db, user_id, avatar_path)
    
    return user

@router.post("/avatar/emoji", response_model=User, summary="使用 emoji 头像")
async def set_emoji_avatar(
    emoji: str,
    user_id: int = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """
    设置 emoji 作为头像
    """
    # 验证 emoji
    if not emoji or len(emoji) > 5:
        raise HTTPException(status_code=400, detail="无效的 emoji")
    
    # 更新用户头像
    user = update_user_avatar(db, user_id, emoji)
    return user

@router.get("/avatar/{user_id}", summary="获取用户头像")
async def get_user_avatar(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取用户头像（公开接口，无需认证）
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    avatar = user.avatar or "👤"
    
    # 如果是 emoji 头像，返回默认图片
    if avatar.startswith("http") or avatar.startswith("/avatars/"):
        # 是图片路径
        if avatar.startswith("/avatars/"):
            file_path = os.path.join(AVATAR_DIR, avatar.split("/")[-1])
            if os.path.exists(file_path):
                return FileResponse(file_path)
    
    # 返回默认头像
    raise HTTPException(status_code=404, detail="头像不存在")