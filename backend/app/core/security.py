"""
安全模块：JWT 认证 + RBAC 权限控制 + 密码加密

认证流程：
1. 用户登录 → 验证密码 → 签发 JWT access_token + refresh_token
2. 每次 API 请求 → 验证 JWT → 提取 user_id 和 role
3. 权限检查 → 根据 role 判断是否有操作权限

RBAC 角色：
- ADMIN: 全部权限
- PI (Principal Investigator): 管理项目、查看项目所有任务
- RESEARCHER: 创建任务、查看自己的任务
- VIEWER: 只读查看
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# OAuth2 方案（从 Authorization: Bearer <token> 提取 token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


# ──────────────────────────────────────────────
# 密码加密
# ──────────────────────────────────────────────


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        True 表示匹配
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ──────────────────────────────────────────────
# JWT Token 管理
# ──────────────────────────────────────────────


def create_access_token(user_id: int, username: str, role: str) -> str:
    """创建 JWT Access Token

    Args:
        user_id: 用户 ID
        username: 用户名
        role: 用户角色

    Returns:
        JWT token 字符串
    """
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(to_encode, settings.validated_secret_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """创建 JWT Refresh Token（用于刷新 access_token）

    Args:
        user_id: 用户 ID

    Returns:
        JWT refresh token 字符串
    """
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(to_encode, settings.validated_secret_key, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码并验证 JWT Token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 token 数据字典

    Raises:
        JWTError: Token 无效或过期
    """
    return jwt.decode(token, settings.validated_secret_key, algorithms=[settings.JWT_ALGORITHM])


# ──────────────────────────────────────────────
# 认证依赖
# ──────────────────────────────────────────────


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI 依赖：从 JWT token 解析当前用户

    每个需要认证的 API 端点注入此依赖即可。

    Args:
        token: 从 Authorization header 提取的 Bearer token

    Returns:
        包含 user_id, username, role 的字典

    Raises:
        HTTPException 401: Token 无效或过期
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
        return {
            "user_id": int(user_id),
            "username": payload.get("username", ""),
            "role": payload.get("role", "RESEARCHER"),
        }
    except JWTError:
        raise credentials_exception


# ──────────────────────────────────────────────
# RBAC 权限控制
# ──────────────────────────────────────────────

# 角色层级：数字越大权限越高
ROLE_HIERARCHY = {
    "VIEWER": 1,
    "RESEARCHER": 2,
    "PI": 3,
    "ADMIN": 4,
}


class PermissionChecker:
    """基于 RBAC 的权限检查器

    用法（FastAPI 依赖工厂）:
        require_role = PermissionChecker.require_role("ADMIN")
        @router.post("/admin/users")
        async def create_user(current_user = Depends(get_current_user), _ = Depends(require_role)):
            ...
    """

    @staticmethod
    def require_role(minimum_role: str):
        """工厂方法：创建一个依赖检查当前用户是否有指定角色

        Args:
            minimum_role: 最低需要的角色名称

        Returns:
            async callable: FastAPI 依赖
        """

        async def role_checker(current_user: dict = Depends(get_current_user)):
            user_role = current_user.get("role", "VIEWER")
            required_level = ROLE_HIERARCHY.get(minimum_role, 4)
            user_level = ROLE_HIERARCHY.get(user_role, 0)

            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要角色: {minimum_role}",
                )

        return role_checker

    @staticmethod
    def require_any_role(*roles: str):
        """工厂方法：用户拥有任一角色即可通过"""

        async def role_checker(current_user: dict = Depends(get_current_user)):
            user_role = current_user.get("role", "VIEWER")
            if user_role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要角色: {', '.join(roles)}",
                )

        return role_checker


# ──────────────────────────────────────────────
# Prompt 注入防护
# ──────────────────────────────────────────────


from app.core.exceptions import PromptInjectionError


def sanitize_prompt(text: str) -> str:
    """检测并清理潜在的 Prompt Injection 攻击

    基础设施层不引入 web 框架依赖，抛出 PromptInjectionError 由
    全局异常处理器统一转换为 HTTP 400。

    Args:
        text: 用户输入文本

    Returns:
        清理后的文本

    Raises:
        PromptInjectionError: 检测到注入攻击
    """
    text_lower = text.lower()
    for pattern in settings.PROMPT_INJECTION_PATTERNS:
        if pattern.lower() in text_lower:
            raise PromptInjectionError(
                message=f"输入包含不安全内容: {pattern}",
                detail={"pattern": pattern},
            )
    return text
