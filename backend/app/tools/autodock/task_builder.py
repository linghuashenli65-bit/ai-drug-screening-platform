"""
Docking 任务构建器

将筛选任务拆分为独立的 Docking 子任务列表。
每个子任务 = 一个药物 + 一个受体，可独立并行执行。
"""

import math
from typing import Any

from app.tools.base import BaseTool, ToolResult


class AutoDockTaskBuilder(BaseTool):
    """Docking 任务拆分工具

    高通量筛选的核心：将大批量药物库拆分为可并行的 Docking 子任务。
    支持按参数分组，为 Worker 集群调度做准备。
    """

    name = "autodock_task_builder"
    description = "将筛选任务拆分为独立可并行的 Docking 子任务"

    def build_tasks(
        self,
        drug_list: list[dict[str, Any]],
        job_id: int,
        receptor_id: int,
        batch_size: int = 100,
    ) -> ToolResult:
        """构建 Docking 子任务列表

        Args:
            drug_list: 药物列表，每项含 drug_id, drug_name, pdbqt_uri
            job_id: 筛选任务 ID
            receptor_id: 受体 ID
            batch_size: 每批任务数（用于进度报告）

        Returns:
            ToolResult 包含 tasks 列表和批次信息
        """
        if not drug_list:
            return ToolResult.failure(error="药物列表为空")

        tasks = []
        for i, drug in enumerate(drug_list):
            task = {
                "job_id": job_id,
                "drug_id": drug["drug_id"],
                "drug_name": drug.get("drug_name", ""),
                "smiles": drug.get("smiles", ""),
                "ligand_pdbqt": drug.get("pdbqt_uri", ""),
                "receptor_id": receptor_id,
                "task_index": i,
                "status": "PENDING",
                "affinity_score": None,
                "retry_count": 0,
                "result_uri": None,
            }
            tasks.append(task)

        # 分组
        num_batches = math.ceil(len(tasks) / batch_size)
        batches = []
        for b in range(num_batches):
            start = b * batch_size
            end = min(start + batch_size, len(tasks))
            batches.append({
                "batch_index": b,
                "task_range": (start, end),
                "count": end - start,
            })

        return ToolResult.success(
            data={
                "total_tasks": len(tasks),
                "total_drugs": len(drug_list),
                "batch_size": batch_size,
                "num_batches": num_batches,
                "tasks": tasks,
                "batches": batches,
            }
        )

    def build_param_grid(
        self,
        receptor_pdbqt: str,
        exhaustiveness_values: list[int] = None,
        box_sizes: list[dict] = None,
    ) -> ToolResult:
        """构建参数网格（用于参数扫描）

        Args:
            receptor_pdbqt: 受体 PDBQT 路径
            exhaustiveness_values: 不同 exhaustiveness 值列表
            box_sizes: 不同盒子尺寸列表

        Returns:
            参数组合列表
        """
        exhaustiveness_values = exhaustiveness_values or [8]
        box_sizes = box_sizes or [{"size_x": 20, "size_y": 20, "size_z": 20}]

        params = []
        for ex in exhaustiveness_values:
            for box in box_sizes:
                params.append({
                    "receptor": receptor_pdbqt,
                    "exhaustiveness": ex,
                    **box,
                })

        return ToolResult.success(data={"param_combinations": params, "count": len(params)})
