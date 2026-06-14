"""
DrugBank 药物知识查询工具

从 MySQL drug_library 表或 DrugBank 数据库中查询药物信息：
- 药物名称、SMILES、适应症
- 药理作用机制
- 已批准的适应症
- 药物相互作用
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.molecule import DrugLibrary
from app.tools.base import BaseTool, ToolResult


class DrugbankQuery(BaseTool):
    """DrugBank 药物知识查询

    查询已上市药物的详细信息和临床数据。
    """

    name = "drugbank_query"
    description = "查询 DrugBank 药物知识库：作用机制、适应症、药理学数据"

    async def query_by_id(self, drug_id: int, db: AsyncSession) -> ToolResult:
        """通过药物 ID 查询

        Args:
            drug_id: 药物 ID (drug_library.id)
            db: 数据库会话

        Returns:
            ToolResult 包含药物详细信息
        """
        result = await db.execute(select(DrugLibrary).where(DrugLibrary.id == drug_id))
        drug = result.scalar_one_or_none()

        if drug is None:
            return ToolResult.failure(error=f"药物 ID={drug_id} 不存在")

        return ToolResult.success(
            data={
                "drug_id": drug.id,
                "drug_name": drug.drug_name,
                "smiles": drug.smiles,
                "drugbank_id": drug.drugbank_id,
                "indication": drug.indication or "",
                "molecular_weight": float(drug.molecular_weight) if drug.molecular_weight else None,
                "logp": float(drug.logp) if drug.logp else None,
            }
        )

    async def query_by_drugbank_id(self, drugbank_id: str, db: AsyncSession) -> ToolResult:
        """通过 DrugBank ID 查询

        Args:
            drugbank_id: DrugBank 数据库 ID (e.g. "DB00001")
            db: 数据库会话

        Returns:
            ToolResult 包含药物详细信息
        """
        result = await db.execute(
            select(DrugLibrary).where(DrugLibrary.drugbank_id == drugbank_id)
        )
        drug = result.scalar_one_or_none()

        if drug is None:
            return ToolResult.failure(error=f"DrugBank ID={drugbank_id} 不存在")

        return ToolResult.success(
            data={
                "drug_id": drug.id,
                "drug_name": drug.drug_name,
                "smiles": drug.smiles,
                "drugbank_id": drug.drugbank_id,
                "indication": drug.indication or "",
            }
        )

    async def search_by_name(self, name: str, db: AsyncSession, limit: int = 10) -> ToolResult:
        """通过药物名称模糊搜索

        Args:
            name: 搜索关键词
            db: 数据库会话
            limit: 返回数量上限

        Returns:
            ToolResult 包含匹配药物列表
        """
        result = await db.execute(
            select(DrugLibrary)
            .where(DrugLibrary.drug_name.ilike(f"%{name}%"))
            .limit(limit)
        )
        drugs = result.scalars().all()

        items = [
            {
                "drug_id": d.id,
                "drug_name": d.drug_name,
                "drugbank_id": d.drugbank_id,
                "indication": d.indication or "",
            }
            for d in drugs
        ]

        return ToolResult.success(data={"drugs": items, "count": len(items)})

    def format_for_llm(self, drug_info: dict) -> str:
        """将药物信息格式化为 LLM 提示用的文本

        Args:
            drug_info: 药物信息字典

        Returns:
            格式化文本
        """
        lines = [
            f"药物名称: {drug_info.get('drug_name', 'N/A')}",
            f"DrugBank ID: {drug_info.get('drugbank_id', 'N/A')}",
            f"SMILES: {drug_info.get('smiles', 'N/A')}",
            f"适应症: {drug_info.get('indication', 'N/A')}",
        ]
        if drug_info.get("molecular_weight"):
            lines.append(f"分子量: {drug_info['molecular_weight']}")
        if drug_info.get("logp"):
            lines.append(f"LogP: {drug_info['logp']}")
        return "\n".join(lines)
