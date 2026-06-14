"""
认证 API — 用户注册、登录、Token 刷新

POST /api/v1/auth/register  — 用户注册
POST /api/v1/auth/login     — 用户登录，返回 JWT token
POST /api/v1/auth/refresh   — 刷新 access token
GET  /api/v1/auth/me        — 获取当前用户信息
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jose import JWTError

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册

    创建新用户账户，返回 JWT token。
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise ConflictError(message="用户名已存在")

    # 创建用户
    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        role="RESEARCHER",
        status=1,
    )
    db.add(user)
    await db.flush()

    # 签发 Token
    access_token = create_access_token(user.id, user.username, "RESEARCHER")
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录

    验证凭据，返回 JWT token pair。
    """
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise AuthenticationError(message="用户名或密码错误")

    if user.status != 1:
        raise AuthenticationError(message="账户已被禁用")

    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新 Access Token

    使用 refresh_token 换取新的 access_token。
    """
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise AuthenticationError(message="无效的 Refresh Token")

        user_id = int(payload.get("sub"))
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.status != 1:
            raise AuthenticationError(message="用户不存在或已禁用")

        access_token = create_access_token(user.id, user.username, user.role)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    except (JWTError, ValueError, KeyError):
        raise AuthenticationError(message="无效的 Refresh Token")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前登录用户信息"""
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(message="用户不存在")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=str(user.created_at) if user.created_at else "",
    )
