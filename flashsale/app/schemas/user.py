from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

class UserBase(BaseModel):
    """
    用户基础模型，用于定义用户的基本字段

    字段说明：
    - username: 用户名，唯一，用于登录
    - name: 用户姓名
    - age: 用户年龄
    - love: 用户喜欢的商品ID列表（可选）
    """
    username: str = Field(..., description="用户名，唯一，用于登录", min_length=3, max_length=50)
    name: str = Field(..., description="用户姓名", max_length=100)
    age: int = Field(..., description="用户年龄", ge=1, le=120)
    love: Optional[List[int]] = Field(default=[], description="用户喜欢的商品ID列表")

class UserCreate(UserBase):
    """
    用户创建模型，用于创建新用户时接收数据
    """
    password: str = Field(..., description="密码", min_length=6, max_length=100)

class UserRegister(BaseModel):
    """
    用户注册模型，用于用户注册时接收数据
    """
    username: str = Field(..., description="用户名，唯一，用于登录", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    name: str = Field(..., description="用户姓名", max_length=100)
    age: int = Field(..., description="用户年龄", ge=1, le=120)

class User(UserBase):
    """
    用户响应模型，用于返回用户信息给客户端

    字段说明：
    - id: 用户ID
    - is_active: 用户状态
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    id: int = Field(..., description="用户ID")
    is_active: int = Field(default=1, description="用户状态，1表示活跃，0表示禁用")
    created_at: Optional[datetime.datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime.datetime] = Field(None, description="更新时间")
    # 用户喜欢的商品ID列表，JSON格式存储，默认为空列表
    love: Optional[List[int]] = Field(default=[], description="用户喜欢的商品ID列表")
    # 用户订单ID列表，JSON格式存储，默认为空列表
    orders: Optional[List[int]] = Field(default=[], description="用户订单ID列表")
    # 用户购物车商品列表，JSON格式存储，默认为空列表
    cart: Optional[List[dict]] = Field(default=[], description="用户购物车商品列表")
    # 用户地址信息，JSON格式存储，默认为空字典
    address: Optional[dict] = Field(default={}, description="用户地址信息")
    # 用户手机号，可选
    phone: Optional[str] = Field(None, description="用户手机号")
    # 用户邮箱，可选
    email: Optional[str] = Field(None, description="用户邮箱")
    #Config配置，将数据库字段映射到模型字段
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    """
    登录请求模型，用于接收登录请求

    字段说明：
    - username: 用户名
    - password: 密码
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    """
    登录响应模型，用于返回登录结果

    字段说明：
    - access_token: JWT访问令牌
    - token_type: 令牌类型
    - user: 用户信息
    """
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: User = Field(..., description="用户信息")

class ErrorResponse(BaseModel):
    """
    错误响应模型，用于返回错误信息

    字段说明：
    - detail: 错误详情
    """
    detail: str = Field(..., description="错误详情")