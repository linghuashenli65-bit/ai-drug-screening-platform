"""
受体服务

受体的增删改查。
"""


class ReceptorService:
    """受体服务"""

    @staticmethod
    async def list_receptors(session, skip: int = 0, limit: int = 50):
        """列出受体"""
        from app.models.receptor import Receptor
        from sqlalchemy import select

        result = await session.execute(
            select(Receptor).offset(skip).limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_receptor(session, receptor_id: int):
        """获取受体详情"""
        from app.models.receptor import Receptor
        from sqlalchemy import select

        result = await session.execute(select(Receptor).where(Receptor.id == receptor_id))
        rec = result.scalar_one_or_none()
        if not rec:
            raise ValueError("Receptor not found")
        return rec

    @staticmethod
    async def create_receptor(session, receptor_name: str, pdb_code: str, description: str = ""):
        """创建受体"""
        from app.models.receptor import Receptor

        receptor = Receptor(
            receptor_name=receptor_name,
            pdb_code=pdb_code,
            description=description,
        )
        session.add(receptor)
        await session.flush()
        return receptor


async def get_all_receptors(session):
    """获取所有受体（独立函数）"""
    return await ReceptorService.list_receptors(session, skip=0, limit=10000)


async def get_receptor_by_id(session, receptor_id: int):
    """按 ID 获取受体（独立函数）"""
    return await ReceptorService.get_receptor(session, receptor_id)
