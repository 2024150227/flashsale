from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.xss import escape_html

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
    添加喜欢的商品

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
    return db_user

def remove_favorite_product(db: Session, user_id: int, product_id: int) -> Optional[User]:
    """
    移除喜欢的商品

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
    return db_user

def get_favorite_products(db: Session, user_id: int) -> List[int]:
    """
    获取用户喜欢的商品ID列表

    参数:
        db: 数据库会话
        user_id: 用户ID

    返回:
        List[int]: 商品ID列表
    """
    db_user = get_user(db, user_id)
    if db_user and db_user.love:
        return db_user.love
    return []