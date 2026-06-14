"""
Database Agent — 药物数据库管理

职责：
- 加载药物数据库（从 MySQL drug_library 表）
- 建立 Milvus 索引（用于相似性检索）
- 过滤候选药物（去除异常记录、去重）
- 批量生成 PDBQT（首次导入时）
- 候选库预筛选（通过 Milvus 相似性检索缩减候选数量）

输入: {"receptor_id": 1, "candidate_fingerprint": [...]}
输出: {"drug_list": [...], "total_drugs": 5000}
"""

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.models.molecule import DrugLibrary
from app.tools.drugbank.query import DrugbankQuery


class DatabaseAgent(BaseAgent):
    """药物库管理 Agent

    从 MySQL 加载药物库，可选通过 Milvus 做相似性预筛选。
    """

    name = "DatabaseAgent"
    description = "加载药物库、建立索引、过滤候选药物"

    def __init__(self):
        super().__init__()
        self.drugbank_query = DrugbankQuery()

    def _validate_input(self, state: dict[str, Any]) -> None:
        pass  # drug_library 加载不需要特定输入

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        fingerprint = state.get("fingerprint", [])
        use_milvus_prescreen = state.get("use_milvus_prescreen", True)
        prescreen_top_k = state.get("prescreen_top_k", 1000)

        # 从 MySQL 加载完整药物库
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            drug_list = await self.load_full_library(db)

        if not drug_list:
            self.logger.warning("药物库为空")

        self.logger.info(f"加载药物库: {len(drug_list)} 个药物")

        if fingerprint and use_milvus_prescreen and drug_list:
            # Milvus 相似性预筛选
            try:
                prescreened = await self._prescreen_by_similarity(
                    fingerprint, prescreen_top_k
                )
                if prescreened:
                    # 将 Milvus 结果与 drug_list 合并
                    prescreened_ids = {hit["drug_id"] for hit in prescreened}
                    drug_list = [d for d in drug_list if d["drug_id"] in prescreened_ids]
                    self.logger.info(f"Milvus 预筛选: {len(drug_list)} 候选药物 (top {prescreen_top_k})")
            except Exception as e:
                self.logger.warning(f"Milvus 预筛选跳过: {e}")

        return {
            "drug_list": drug_list,
            "total_drugs": len(drug_list),
            "prescreen_enabled": use_milvus_prescreen and bool(fingerprint),
            "prescreen_top_k": prescreen_top_k if fingerprint else None,
            "library_loaded": True,
        }

    async def _prescreen_by_similarity(
        self, fingerprint: list[int], top_k: int
    ) -> list[dict]:
        """通过 Milvus 相似性检索预筛选候选药物"""
        from app.core.milvus import search_similar_drugs

        try:
            similar = await search_similar_drugs(fingerprint, top_k=top_k)
            return [
                {
                    "drug_id": hit["drug_id"],
                    "drug_name": hit["drug_name"],
                    "similarity_distance": hit["distance"],
                }
                for hit in similar
            ]
        except Exception as e:
            self.logger.warning(f"Milvus 预筛选失败: {e}，使用全部药物库")
            return []

    async def load_full_library(self, db: AsyncSession) -> list[dict[str, Any]]:
        """从 MySQL 加载完整药物库

        Args:
            db: 数据库会话

        Returns:
            药物列表
        """
        result = await db.execute(select(DrugLibrary))
        drugs = result.scalars().all()

        return [
            {
                "drug_id": d.id,
                "drug_name": d.drug_name,
                "smiles": d.smiles,
                "drugbank_id": d.drugbank_id,
                "pdbqt_uri": d.pdbqt_uri,
                "molecular_weight": float(d.molecular_weight) if d.molecular_weight else None,
                "logp": float(d.logp) if d.logp else None,
            }
            for d in drugs
        ]

    async def get_library_count(self, db: AsyncSession) -> int:
        """获取药物库总数"""
        result = await db.execute(select(func.count(DrugLibrary.id)))
        return result.scalar() or 0

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "drug_list": output.get("drug_list", []),
            "total_drugs": output.get("total_drugs", 0),
            "prescreen_enabled": output.get("prescreen_enabled", False),
            "library_loaded": output.get("library_loaded", False),
        }
