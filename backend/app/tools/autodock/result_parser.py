"""
AutoDock Vina 结果解析器

从 Vina 输出 PDBQT 文件中解析：
- 各 binding mode 的亲和力分数
- 各 mode 的 RMSD 值
- 最优亲和力分数
"""

import os
import re
from typing import Any, Optional

from app.tools.base import BaseTool, ToolResult


class AutoDockResultParser(BaseTool):
    """Docking 结果解析工具

    从 Vina 输出 PDBQT 文件中提取 docked poses 的 affinity 信息。
    """

    name = "autodock_result_parser"
    description = "从 Vina PDBQT 输出解析 binding poses 和 affinity"

    def parse(
        self,
        output_pdbqt: str,
        extract_all_modes: bool = False,
    ) -> ToolResult:
        """解析 Vina 对接输出

        Args:
            output_pdbqt: Vina 输出 PDBQT 文件路径
            extract_all_modes: 是否提取所有 mode 的分数（False 只取最优）

        Returns:
            ToolResult 包含 binding poses 列表
        """
        if not os.path.exists(output_pdbqt):
            return ToolResult.failure(error=f"输出文件不存在: {output_pdbqt}")

        with open(output_pdbqt, "r") as f:
            content = f.read()

        # 使用 Vina 标准输出格式解析
        # 每个 MODEL 块包含 REMARK VINA RESULT
        model_pattern = re.compile(
            r"MODEL\s+(\d+).*?REMARK VINA RESULT:\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)",
            re.DOTALL,
        )
        matches = model_pattern.findall(content)

        if not matches:
            return ToolResult.failure(error="未找到有效的 Docking 结果", data={"content_head": content[:500]})

        modes = []
        for model_idx, affinity, rmsd_lb, rmsd_ub in matches:
            modes.append({
                "model": int(model_idx),
                "affinity_kcal_mol": float(affinity),
                "rmsd_lower_bound": float(rmsd_lb),
                "rmsd_upper_bound": float(rmsd_ub),
            })

        # 按 affinity 升序排列（越负越好）
        modes.sort(key=lambda x: x["affinity_kcal_mol"])

        best = modes[0]

        return ToolResult.success(
            data={
                "best_affinity": best["affinity_kcal_mol"],
                "best_rmsd_lb": best["rmsd_lb"],
                "best_rmsd_ub": best["rmsd_ub"],
                "num_modes_found": len(modes),
                "all_modes": modes if extract_all_modes else [],
            }
        )

    def parse_vina_log(self, log_text: str) -> ToolResult:
        """从 Vina stdout 日志中解析结果（备选方案）

        Args:
            log_text: Vina 标准输出文本

        Returns:
            ToolResult 包含解析结果
        """
        # Vina stdout 格式:
        # mode |   affinity | dist from best mode
        #      | (kcal/mol) | rmsd l.b.| rmsd u.b.
        # -----+------------+----------+----------
        #    1 |      -9.2  |      0.0 |      0.0

        lines = log_text.split("\n")
        modes = []
        in_table = False

        for line in lines:
            line = line.strip()
            if line.startswith("mode") or line.startswith("-----"):
                in_table = True
                continue
            if in_table and line:
                parts = line.split()
                if len(parts) >= 4 and parts[0].isdigit():
                    modes.append({
                        "model": int(parts[0]),
                        "affinity_kcal_mol": float(parts[1]),
                        "rmsd_lower_bound": float(parts[2]),
                        "rmsd_upper_bound": float(parts[3]),
                    })

        if not modes:
            return ToolResult.failure(error="无法从日志解析 Docking 结果", data={"log": log_text[:500]})

        modes.sort(key=lambda x: x["affinity_kcal_mol"])
        best = modes[0]

        return ToolResult.success(
            data={
                "best_affinity": best["affinity_kcal_mol"],
                "num_modes_found": len(modes),
                "all_modes": modes,
            }
        )
