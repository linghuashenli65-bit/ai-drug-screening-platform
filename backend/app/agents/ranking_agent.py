"""
Ranking Agent — 结果排序与统计分析

职责：
- 按 Binding Score 排序（升序，越负越好）
- Top-N 筛选（Top 100 / Top 20）
- 统计分析（分布、中位数、四分位数）
- 结合能力分类（STRONG / MODERATE / WEAK）

输入: {"docking_results": [...]}
输出: {"top_hits": [...], "statistics": {...}, "ranking_complete": true}
"""

from typing import Any

from app.agents.base import BaseAgent
from app.tools.autodock.score_extractor import AutoDockScoreExtractor


class RankingAgent(BaseAgent):
    """结果排序 Agent

    从 Docking 结果中提取 Binding Score，按亲和力排序并生成 Top-N 列表。
    """

    name = "RankingAgent"
    description = "Docking 结果排序、Top-N 筛选、统计分析"

    def __init__(self):
        super().__init__()
        self.score_extractor = AutoDockScoreExtractor()

    def _validate_input(self, state: dict[str, Any]) -> None:
        results = state.get("docking_results", [])
        if not results:
            raise ValueError("RankingAgent: docking_results 为空")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        docking_results = state["docking_results"]
        top_n = state.get("top_n", 100)

        # 提取 Top-N
        extract_result = self.score_extractor.extract_top_n(
            docking_results=docking_results,
            top_n=top_n,
        )

        if not extract_result.success:
            return {"ranking_error": extract_result.error}

        # 分类
        top_hits = extract_result.data.get("top_hits", [])
        categories = {"STRONG": 0, "MODERATE": 0, "WEAK": 0, "VERY_WEAK": 0}
        for hit in top_hits:
            cat = self.score_extractor.compute_binding_category(hit["affinity_score"])
            categories[cat] += 1

        return {
            "top_hits": top_hits,
            "statistics": extract_result.data.get("statistics", {}),
            "categories": categories,
            "total_valid": extract_result.data.get("total_valid", 0),
            "total_docked": extract_result.data.get("total_docked", 0),
            "success_rate": extract_result.data.get("success_rate", 0),
        }

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "top_hits": output.get("top_hits", []),
            "statistics": output.get("statistics", {}),
            "categories": output.get("categories", {}),
            "total_valid": output.get("total_valid", 0),
            "success_rate": output.get("success_rate", 0),
            "ranking_complete": "ranking_error" not in output,
        }
