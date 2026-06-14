"""
管理员服务

系统配置、审计日志管理。
"""


class AdminService:
    """管理员服务"""

    @staticmethod
    async def update_config(session, key: str, value: str):
        """更新系统配置"""
        return {"key": key, "value": value, "updated": True}

    @staticmethod
    async def get_audit_logs(session, skip: int = 0, limit: int = 50):
        """获取审计日志"""
        from app.models.audit import AuditLog
        from sqlalchemy import select

        result = await session.execute(
            select(AuditLog).offset(skip).limit(limit)
        )
        return result.scalars().all()
