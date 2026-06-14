"""
药物库服务

药物库的导入、查询和管理。
"""


class DrugLibraryService:
    """药物库服务"""

    @staticmethod
    async def import_library(session, file_path: str):
        """导入药物库"""
        return {"imported": 0, "message": f"Import from {file_path} queued"}

    @staticmethod
    async def get_drugs_paginated(session, skip: int = 0, limit: int = 50):
        """分页获取药物"""
        from app.models.molecule import DrugLibrary
        from sqlalchemy import select

        result = await session.execute(
            select(DrugLibrary).offset(skip).limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def search_drugs(session, query: str):
        """搜索药物"""
        from app.models.molecule import DrugLibrary
        from sqlalchemy import select

        result = await session.execute(
            select(DrugLibrary).where(DrugLibrary.drug_name.contains(query))
        )
        return result.scalars().all()

    @staticmethod
    async def bulk_import_drugs(session, drugs: list):
        """批量导入药物"""
        from app.models.molecule import DrugLibrary

        count = 0
        for d in drugs:
            drug = DrugLibrary(**d)
            session.add(drug)
            count += 1
        await session.flush()
        return {"imported": count}


async def get_drugs_paginated(session, skip: int = 0, limit: int = 50):
    """分页获取药物（独立函数）"""
    return await DrugLibraryService.get_drugs_paginated(session, skip, limit)


async def search_drugs(session, query: str):
    """搜索药物（独立函数）"""
    return await DrugLibraryService.search_drugs(session, query)


async def bulk_import_drugs(session, drugs: list):
    """批量导入药物（独立函数）"""
    return await DrugLibraryService.bulk_import_drugs(session, drugs)
