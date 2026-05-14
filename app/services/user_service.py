from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, get_redis_client
from app.core.xss import escape_html

# Redis缓存键前缀
FAVORITES_KEY_PREFIX = "flashsale:user:favorites:"

def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    根据用户ID获取用户信息

    参数:
        db: 数据库会话
        user_id: 用户ID

    返回:
        Optional[User]: 用户对象，如果不存在返回None
    """
    return db.query(User).filter(User.id == user_id, User.is_active == 1).first()

# 为get_user_by_username方法添加权重、参数、返回值和异常处理说明
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    根据用户名获取用户信息

    权重：1（低频率，但最重要）
    参数：
        db: 数据库会话
        username: 用户名
    返回：
        Optional[User]: 用户对象，如果不存在返回None
    异常处理：
        404: 用户不存在，返回404错误
    """
    return db.query(User).filter(User.username == username, User.is_active == 1).first()

def create_user(db: Session, user: UserCreate) -> User:
    """
    创建新用户

    权重：1（低频率，但最重要）
    参数：
        db: 数据库会话
        user: 用户创建数据
    返回：
        User: 创建的用户对象
    """
    db_user = User(
        username=escape_html(user.username),
        hashed_password=hash_password(user.password),
        name=escape_html(user.name),
        age=user.age,
        love=user.love if user.love else []
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_data: dict) -> Optional[User]:
    """
    更新用户信息

    权重：1（低频率，但最重要）
    参数：
        db: 数据库会话
        user_id: 用户ID
        user_data: 要更新的用户数据
    返回：
        Optional[User]: 更新后的用户对象，如果不存在返回None
    """
    db_user = get_user(db, user_id)
    if db_user:
        for key, value in user_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """
    删除用户（软删除）

    参数:
        db: 数据库会话
        user_id: 用户ID

    返回:
        bool: 是否删除成功
    """
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_active = 0
        db.commit()
        return True
    return False

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """
    获取用户列表

    参数:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的记录数

    返回:
        List[User]: 用户列表
    """
    return db.query(User).filter(User.is_active == 1).offset(skip).limit(limit).all()

def add_favorite_product(db: Session, user_id: int, product_id: int) -> Optional[User]:
    """
    添加喜欢的商品（同步到Redis）

    权重：1（低频率，但最重要）
    参数：
        db: 数据库会话
        user_id: 用户ID
        product_id: 商品ID
    返回：
        Optional[User]: 更新后的用户对象，如果不存在返回None
    """
    db_user = get_user(db, user_id)
    if db_user:
        if db_user.love is None:
            db_user.love = []
        if product_id not in db_user.love:
            db_user.love.append(product_id)
            db.commit()
            db.refresh(db_user)
            
            # 同步到Redis
            redis = get_redis_client()
            if redis:
                favorites_key = f"{FAVORITES_KEY_PREFIX}{user_id}"
                redis.sadd(favorites_key, product_id)
                redis.expire(favorites_key, 24 * 60 * 60)  # 24小时过期
    return db_user

def remove_favorite_product(db: Session, user_id: int, product_id: int) -> Optional[User]:
    """
    移除喜欢的商品（同步到Redis）

    权重：1（低频率，但最重要）
    参数：
        db: 数据库会话
        user_id: 用户ID
        product_id: 商品ID
    返回：
        Optional[User]: 更新后的用户对象，如果不存在返回None
    """
    db_user = get_user(db, user_id)
    if db_user and db_user.love and product_id in db_user.love:
        db_user.love.remove(product_id)
        db.commit()
        db.refresh(db_user)
        
        # 同步到Redis
        redis = get_redis_client()
        if redis:
            favorites_key = f"{FAVORITES_KEY_PREFIX}{user_id}"
            redis.srem(favorites_key, product_id)
    return db_user

def get_favorite_products(db: Session, user_id: int) -> List[int]:
    """
    获取用户喜欢的商品ID列表（优先从Redis获取）

    参数:
        db: 数据库会话
        user_id: 用户ID

    返回:
        List[int]: 商品ID列表
    """
    # 优先从Redis获取
    redis = get_redis_client()
    favorites_key = f"{FAVORITES_KEY_PREFIX}{user_id}"
    
    if redis:
        redis_favorites = redis.smembers(favorites_key)
        if redis_favorites:
            return [int(pid) for pid in redis_favorites]
    
    # Redis中没有，从数据库获取
    db_user = get_user(db, user_id)
    if db_user and db_user.love:
        # 同步到Redis
        if redis:
            for product_id in db_user.love:
                redis.sadd(favorites_key, product_id)
            redis.expire(favorites_key, 24 * 60 * 60)
        return db_user.love
    
    return []

def update_user_avatar(db: Session, user_id: int, avatar: str) -> Optional[User]:
    """
    更新用户头像

    参数:
        db: 数据库会话
        user_id: 用户ID
        avatar: 头像内容（emoji或图片路径）

    返回:
        Optional[User]: 更新后的用户对象，如果不存在返回None
    """
    db_user = get_user(db, user_id)
    if db_user:
        db_user.avatar = avatar
        db.commit()
        db.refresh(db_user)
    return db_user