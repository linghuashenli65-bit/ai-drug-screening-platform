"""
LLM Chain 调用链

封装多步 LLM 调用流程，支持 Prompt 模板填充和 Chain 组合。
"""

from typing import Any

from app.tools.base import ToolResult
from app.tools.llm.client import LLMClient


class LLMChain:
    """LLM 调用链

    组合 Prompt 模板 + LLM Client，提供便捷的分析调用接口。
    """

    def __init__(self):
        self.client = LLMClient()

    async def analyze_docking_results(
        self,
        receptor_name: str,
        pdb_code: str,
        docking_results: list[dict[str, Any]],
    ) -> ToolResult:
        """分析 Docking 结果

        Args:
            receptor_name: 受体名称
            pdb_code: PDB 代码
            docking_results: Top Hits 对接结果列表

        Returns:
            ToolResult 包含 AI 分析文本
        """
        from app.tools.llm.prompts.analysis import DOCKING_ANALYSIS_PROMPT

        # 构建表格化的对接结果
        results_text = ""
        for i, hit in enumerate(docking_results[:10], 1):
            results_text += (
                f"| {i} | {hit.get('drug_name', 'N/A')} | "
                f"{hit.get('affinity_score', 'N/A')} | "
                f"{hit.get('drugbank_id', 'N/A')} |\n"
            )

        prompt = DOCKING_ANALYSIS_PROMPT.format(
            receptor_name=receptor_name,
            pdb_code=pdb_code,
            docking_results=results_text,
        )

        return await self.client.chat(
            messages=[
                {"role": "system", "content": "你是一位经验丰富的计算药物化学专家。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

    async def analyze_single_drug(
        self,
        drug_info: dict[str, Any],
        affinity_score: float,
        interactions: str,
        pubmed_articles: str = "无相关文献",
    ) -> ToolResult:
        """分析单个候选药物

        Args:
            drug_info: 药物信息字典
            affinity_score: 结合亲和力
            interactions: 相互作用描述文本
            pubmed_articles: PubMed 文献摘要

        Returns:
            ToolResult 包含 AI 分析文本
        """
        from app.tools.llm.prompts.analysis import DRUG_DETAIL_ANALYSIS_PROMPT

        prompt = DRUG_DETAIL_ANALYSIS_PROMPT.format(
            drug_name=drug_info.get("drug_name", "N/A"),
            drugbank_id=drug_info.get("drugbank_id", "N/A"),
            indication=drug_info.get("indication", "N/A"),
            smiles=drug_info.get("smiles", "N/A"),
            molecular_weight=drug_info.get("molecular_weight", "N/A"),
            logp=drug_info.get("logp", "N/A"),
            affinity_score=affinity_score,
            interactions=interactions,
            pubmed_articles=pubmed_articles,
        )

        return await self.client.chat(
            messages=[
                {"role": "system", "content": "你是一位专业的药物化学家，擅长药物重定位分析。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

    async def generate_report_summary(
        self,
        job_name: str,
        receptor_name: str,
        total_drugs: int,
        top_hits: list[dict[str, Any]],
        analysis_text: str,
    ) -> ToolResult:
        """生成报告摘要

        Args:
            job_name: 任务名称
            receptor_name: 受体名称
            total_drugs: 筛选药物总数
            top_hits: Top Hits 列表
            analysis_text: AI 分析文本

        Returns:
            ToolResult 包含摘要文本
        """
        prompt = f"""你是一位科学报告编辑。请为以下虚拟筛选结果撰写中文摘要。

## 筛选任务
- 任务名称: {job_name}
- 靶点: {receptor_name}
- 筛选药物数: {total_drugs}
- Top Hits: {len(top_hits)} 个候选

## Top 3 候选
"""
        for hit in top_hits[:3]:
            prompt += f"- {hit['drug_name']}: {hit['affinity_score']} kcal/mol\n"

        prompt += f"""
## AI分析要点
{analysis_text[:1000]}

请撰写一段200-300字的中文摘要，包含筛选目的、方法、关键发现和下一步建议。
"""

        return await self.client.chat(
            messages=[
                {"role": "system", "content": "你是一位科学报告编辑。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1024,
        )
