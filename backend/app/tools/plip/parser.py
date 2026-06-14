"""
PLIP 结果解析器

将 PLIP 原始输出解析为结构化的相互作用数据，
支持 JSON 输出供 AI 分析使用。
"""

import json
from typing import Any

from app.tools.base import BaseTool, ToolResult


class PlipParser(BaseTool):
    """PLIP 分析结果解析工具

    将 PLIP 交互分析结果转换为适合 LLM 分析的结构化 JSON。
    """

    name = "plip_parser"
    description = "解析和格式化 PLIP 相互作用数据"

    def format_for_llm(self, plip_result: dict[str, Any]) -> ToolResult:
        """将 PLIP 结果格式化为 LLM 友好的文本

        Args:
            plip_result: PLIP 分析结果字典

        Returns:
            ToolResult 包含格式化文本
        """
        lines = []
        lines.append("## 蛋白-配体相互作用分析")
        lines.append("")

        if plip_result.get("hydrogen_bonds", 0) > 0:
            lines.append(f"- 氢键: {plip_result['hydrogen_bonds']} 个")
        if plip_result.get("hydrophobic_contacts", 0) > 0:
            lines.append(f"- 疏水接触: {plip_result['hydrophobic_contacts']} 个")
        if plip_result.get("salt_bridges", 0) > 0:
            lines.append(f"- 盐桥: {plip_result['salt_bridges']} 个")
        if plip_result.get("pi_interactions", 0) > 0:
            lines.append(f"- Pi 相互作用: {plip_result['pi_interactions']} 个")

        lines.append(f"\n总计非共价相互作用: {plip_result.get('total_interactions', 0)}")

        # 详细残基列表
        analysis_json = plip_result.get("analysis_json", {})
        if "hydrogen_bonds" in analysis_json and analysis_json["hydrogen_bonds"]:
            lines.append("\n### 关键氢键残基")
            for hb in analysis_json["hydrogen_bonds"][:5]:
                lines.append(f"- {hb['residue']} (距离: {hb['distance']}A)")

        return ToolResult.success(data={"formatted_text": "\n".join(lines)})

    def to_json(self, plip_result: dict[str, Any]) -> ToolResult:
        """将 PLIP 结果序列化为 JSON

        Args:
            plip_result: PLIP 分析结果字典

        Returns:
            ToolResult 包含 JSON 字符串
        """
        return ToolResult.success(
            data={
                "json": json.dumps(plip_result, ensure_ascii=False, default=str),
                "interactions": plip_result,
            }
        )
