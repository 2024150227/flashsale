import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.db.session import Base

class User(Base):
    """
    用户模型类，用于存储用户信息
    
    字段说明：
    - id: 用户唯一标识，自增主键
    - username: 用户名，唯一，用于登录
    - hashed_password: 密码哈希值，使用bcrypt加密存储
    - name: 用户姓名
    - age: 用户年龄
    - love: 用户喜欢的商品ID列表，使用JSON格式存储
    - is_active: 用户状态，1表示活跃，0表示禁用
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "users"
    
    # 用户ID，主键，自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 用户名，唯一，用于登录
    username = Column(String(50), unique=True, nullable=False, index=True)
    # 密码哈希值，使用bcrypt加密存储
    hashed_password = Column(String(255), nullable=False)
    # 用户姓名
    name = Column(String(100), nullable=False)
    # 用户年龄
    age = Column(Integer, nullable=False)
    # 用户喜欢的商品ID列表，JSON格式存储，默认为空列表
    love = Column(JSON, default=[])
    # 用户状态，1表示活跃，0表示禁用
    is_active = Column(Integer, default=1)
    # 创建时间
    created_at = Column(DateTime, default=datetime.datetime.now)
    # 更新时间
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)