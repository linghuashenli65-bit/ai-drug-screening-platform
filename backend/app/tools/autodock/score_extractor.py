"""
Score 提取器

从多个 Docking 结果中批量提取 affinity scores，
生成可用于排序和分析的数据表。
"""

from typing import Any

from app.tools.base import BaseTool, ToolResult


class AutoDockScoreExtractor(BaseTool):
    """Binding Score 批量提取工具

    从大量 Docking 任务结果中提取亲和力分数，
    生成排序和分析所需的标准化数据。
    """

    name = "autodock_score_extractor"
    description = "批量提取 Docking 亲和力分数并生成 Top-N 列表"

    def extract_top_n(
        self,
        docking_results: list[dict[str, Any]],
        top_n: int = 100,
    ) -> ToolResult:
        """从 Docking 结果列表提取 Top-N Hits

        Args:
            docking_results: 对接结果列表，每项含 drug_id, drug_name, affinity_score
            top_n: 返回 Top N 个结果

        Returns:
            ToolResult 包含按 affinity 排序的 Top-N 列表和统计信息
        """
        # 过滤无结果或失败的
        valid = [r for r in docking_results if r.get("affinity_score") is not None]

        if not valid:
            return ToolResult.failure(error="无有效 Docking 结果")

        # 按 affinity 升序排序（越低越好）
        valid.sort(key=lambda x: x["affinity_score"])

        # Top-N
        top_hits = []
        for rank, item in enumerate(valid[:top_n], 1):
            top_hits.append({
                "rank": rank,
                "drug_id": item["drug_id"],
                "drug_name": item.get("drug_name", ""),
                "affinity_score": item["affinity_score"],
            })

        # 统计
        scores = [r["affinity_score"] for r in valid]
        scores.sort()

        return ToolResult.success(
            data={
                "total_valid": len(valid),
                "total_docked": len(docking_results),
                "success_rate": len(valid) / len(docking_results) if docking_results else 0,
                "top_n": len(top_hits),
                "top_hits": top_hits,
                "statistics": {
                    "best_score": scores[0],
                    "worst_score": scores[-1],
                    "median_score": scores[len(scores) // 2],
                    "mean_score": sum(scores) / len(scores),
                    "q25_score": scores[len(scores) // 4],
                    "q75_score": scores[3 * len(scores) // 4],
                },
            }
        )

    def compute_binding_category(self, score: float) -> str:
        """根据亲和力分数对结合能力分类

        Args:
            score: 亲和力分数 (kcal/mol)

        Returns:
            结合能力类别
        """
        if score <= -9.0:
            return "STRONG"     # 强结合
        elif score <= -7.0:
            return "MODERATE"   # 中等结合
        elif score <= -5.0:
            return "WEAK"       # 弱结合
        else:
            return "VERY_WEAK"  # 极弱/无结合
