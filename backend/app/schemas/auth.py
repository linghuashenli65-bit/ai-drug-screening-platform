"""
认证相关 Pydantic 模型
"""

from pydantic import BaseModel, EmailStr, Field


# ── 请求 ──


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=2, max_length=64)
    email: str = Field(..., max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class RefreshTokenRequest(BaseModel):
    """刷新 Access Token 请求"""
    refresh_token: str = Field(..., description="刷新令牌")


# ── 响应 ──


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    role: str
    status: int
    created_at: str


class UserBrief(BaseModel):
    """用户简要信息（嵌入其他响应）"""
    id: int
    username: str
