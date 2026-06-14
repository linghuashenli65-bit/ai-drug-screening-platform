"""
Analysis Agent — AI 智能分析

职责：
- LLM 分析：对 Top Hits 进行智能解读
- DrugBank 查询：获取候选药物临床信息
- PubMed 检索：查找相关科学文献
- PLIP 分析：蛋白-配体相互作用分析
- 生成：结合能力评价、药物重定位分析、风险评估、实验建议

输入: {"top_hits": [...], "receptor_name": "...", "pdb_code": "..."}
输出: {"ai_analysis": {...}, "drug_details": [...], "recommendations": [...]}
"""

from typing import Any

from app.agents.base import BaseAgent
from app.tools.llm.chains import LLMChain
from app.tools.llm.client import LLMClient


class AnalysisAgent(BaseAgent):
    """AI 分析 Agent

    调用 LLM 对筛选结果进行多维度智能分析：
    - Docking 结果总体评价
    - Top 候选药物详细分析
    - 药物重定位潜力评估
    - 风险评估与实验建议
    """

    name = "AnalysisAgent"
    description = "LLM 多维度分析、DrugBank 查询、PubMed 检索、药物重定位评估"

    def __init__(self):
        super().__init__()
        self.llm_chain = LLMChain()
        self.llm_client = LLMClient()

    def _validate_input(self, state: dict[str, Any]) -> None:
        top_hits = state.get("top_hits", [])
        if not top_hits:
            raise ValueError("AnalysisAgent: top_hits 为空，无法进行分析")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        top_hits = state.get("top_hits", [])
        receptor_name = state.get("receptor_name", "Unknown Receptor")
        pdb_code = state.get("pdb_code", "")

        try:
            return await self._run_llm_analysis(state, top_hits, receptor_name, pdb_code)
        except Exception as e:
            self.logger.warning(f"LLM 分析失败，使用降级结果: {e}")
            return self._fallback_analysis(top_hits, receptor_name)

    async def _run_llm_analysis(self, state, top_hits, receptor_name, pdb_code):
        """调用 LLM 进行完整分析"""
        # Step 1: Docking 结果总体分析
        docking_analysis = await self.llm_chain.analyze_docking_results(
            receptor_name=receptor_name,
            pdb_code=pdb_code,
            docking_results=top_hits[:20],
        )

        # Step 2: Top 3 候选药物详细分析
        top3_analyses = []
        analysis_top_n = state.get("analysis_top_n", 3)
        for hit in top_hits[:analysis_top_n]:
            drug_result = await self.llm_chain.analyze_single_drug(
                drug_info={
                    "drug_name": hit.get("drug_name", "Unknown"),
                    "drugbank_id": hit.get("drugbank_id", ""),
                    "smiles": hit.get("smiles", ""),
                },
                affinity_score=hit.get("affinity_score", 0),
                interactions=hit.get("interactions", "无详细相互作用数据"),
                pubmed_articles=hit.get("pubmed_articles", "无相关文献"),
            )
            top3_analyses.append({
                "drug_name": hit.get("drug_name"),
                "affinity_score": hit.get("affinity_score"),
                "analysis": drug_result.data.get("content", "") if drug_result.success else "",
            })

        # Step 3: 生成报告摘要
        report_summary = await self.llm_chain.generate_report_summary(
            job_name=state.get("job_name", ""),
            receptor_name=receptor_name,
            total_drugs=state.get("total_drugs", 0),
            top_hits=top_hits[:10],
            analysis_text=docking_analysis.data.get("content", ""),
        )

        return {
            "overall_analysis": docking_analysis.data.get("content", ""),
            "top_drug_analyses": top3_analyses,
            "report_summary": report_summary.data.get("content", ""),
            "model_used": docking_analysis.data.get("model", "unknown"),
            "analysis_complete": True,
        }

    def _fallback_analysis(self, top_hits, receptor_name):
        """LLM 不可用时的降级分析结果"""
        top3 = [
            {
                "drug_name": h.get("drug_name", "Unknown"),
                "affinity_score": h.get("affinity_score"),
                "analysis": f"结合亲和力: {h.get('affinity_score', 'N/A')} kcal/mol",
            }
            for h in top_hits[:3]
        ]
        return {
            "overall_analysis": f"针对 {receptor_name} 的虚拟筛选完成，共筛选 {len(top_hits)} 个候选药物。"
                                f"最佳结合亲和力为 {top_hits[0].get('affinity_score', 'N/A')} kcal/mol。"
                                f"（LLM 分析暂不可用，仅提供基础统计数据）",
            "top_drug_analyses": top3,
            "report_summary": f"筛选完成，Top 1: {top_hits[0].get('drug_name', 'N/A')} "
                              f"({top_hits[0].get('affinity_score', 'N/A')} kcal/mol)" if top_hits else "无结果",
            "model_used": "fallback",
            "analysis_complete": True,
        }

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "overall_analysis": output.get("overall_analysis", ""),
            "top_drug_analyses": output.get("top_drug_analyses", []),
            "report_summary": output.get("report_summary", ""),
            "model_used": output.get("model_used", ""),
            "analysis_complete": output.get("analysis_complete", False),
        }
