"""
认证服务

用户登录、注册、权限管理。
"""

# Module-level re-exports for test mocking
from app.core.security import create_access_token, hash_password, verify_password


class AuthService:
    """认证服务"""

    @staticmethod
    async def login(session, username: str, password: str):
        """用户登录"""
        from app.models.user import User
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Invalid credentials")

        from app.core.security import verify_password, create_access_token
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        token = create_access_token(user_id=user.id, username=user.username, role=user.role)
        return {"access_token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}

    @staticmethod
    async def register(session, username: str, email: str, password: str, role: str = "RESEARCHER"):
        """用户注册"""
        from app.models.user import User
        from sqlalchemy import select
        from app.core.security import hash_password

        result = await session.execute(select(User).where(User.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Username already exists")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
            status=1,
        )
        session.add(user)
        await session.flush()
        return {"id": user.id, "username": user.username}

    @staticmethod
    async def register_by_admin(session, username: str, email: str, password: str, role: str):
        """管理员创建用户"""
        return await AuthService.register(session, username, email, password, role)

    @staticmethod
    async def update_user_status(session, user_id: int, status: int):
        """更新用户状态"""
        from app.models.user import User
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        user.status = status
        await session.flush()
        return {"id": user.id, "status": user.status}


# Module-level functions for test mocking
async def get_user_by_username(session, username: str):
    """按用户名查询用户"""
    from app.models.user import User
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(session, email: str):
    """按邮箱查询用户"""
    from app.models.user import User
    from sqlalchemy import select

    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(session, username: str, email: str, password_hash: str, role: str = "RESEARCHER"):
    """创建用户"""
    from app.models.user import User

    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        status=1,
    )
    session.add(user)
    await session.flush()
    return user
