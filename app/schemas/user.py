from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

class UserBase(BaseModel):
    username: str = Field(..., description="用户名，唯一，用于登录", min_length=3, max_length=50)
    name: str = Field(..., description="用户姓名", max_length=100)
    age: int = Field(..., description="用户年龄", ge=1, le=120)
    avatar: str = Field(default="👤", description="用户头像（emoji表情）")
    love: Optional[List[int]] = Field(default=[], description="用户喜欢的商品ID列表")

class UserCreate(UserBase):
    password: str = Field(..., description="密码", min_length=6, max_length=100)

class UserRegister(BaseModel):
    username: str = Field(..., description="用户名，唯一，用于登录", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)
    name: str = Field(..., description="用户姓名", max_length=100)
    age: int = Field(..., description="用户年龄", ge=1, le=120)
    avatar: str = Field(default="👤", description="用户头像（emoji表情）")

class User(UserBase):
    id: int = Field(..., description="用户ID")
    is_active: int = Field(default=1, description="用户状态，1表示活跃，0表示禁用")
    created_at: Optional[datetime.datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime.datetime] = Field(None, description="更新时间")
    love: Optional[List[int]] = Field(default=[], description="用户喜欢的商品ID列表")
    orders: Optional[List[int]] = Field(default=[], description="用户订单ID列表")
    cart: Optional[List[dict]] = Field(default=[], description="用户购物车商品列表")
    address: Optional[dict] = Field(default={}, description="用户地址信息")
    phone: Optional[str] = Field(None, description="用户手机号")
    email: Optional[str] = Field(None, description="用户邮箱")

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: User = Field(..., description="用户信息")

class RefreshResponse(BaseModel):
    access_token: str = Field(..., description="新的JWT访问令牌")
    refresh_token: str = Field(..., description="新的刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="错误详情")