"""
Planner Agent — 任务规划与状态控制

职责：
- 任务规划：根据 task_id 确定执行步骤
- 节点路由：决定下一个需要执行的 Agent
- 状态流转：控制 CREATED→PREPARING→DOCKING→ANALYZING→REPORTING→COMPLETED
- 断点恢复：检测中断任务并从断点继续
"""

from typing import Any

from app.core.constants import JobStatus, can_transition
from app.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    """任务规划 Agent

    输入: {"task_id": "..."}
    输出: {"next_step": "molecule_agent" | "docking_agent" | ...}
    """

    name = "PlannerAgent"
    description = "负责任务规划、节点路由和状态控制"

    # 正常流程顺序
    FLOW_STEPS = [
        JobStatus.PREPARING,
        JobStatus.DOCKING,
        JobStatus.ANALYZING,
        JobStatus.REPORTING,
        JobStatus.COMPLETED,
    ]

    # 状态到 Agent 映射
    STATE_AGENT_MAP = {
        JobStatus.PREPARING: "molecule_agent",
        JobStatus.DOCKING: "docking_agent",
        JobStatus.ANALYZING: "analysis_agent",
        JobStatus.REPORTING: "report_agent",
    }

    def _validate_input(self, state: dict[str, Any]) -> None:
        if not state.get("task_id"):
            raise ValueError("PlannerAgent: 缺少 task_id")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        current_status = JobStatus(state.get("job_status", JobStatus.CREATED))

        if current_status == JobStatus.CREATED:
            # 首次启动，进入 PREPARING
            return self._plan_first_step(state)

        if current_status == JobStatus.FAILED:
            # 失败恢复
            return self._plan_recovery(state)

        if current_status == JobStatus.RETRYING:
            # 重试中，回到上一状态
            return self._plan_retry(state)

        if current_status == JobStatus.WAIT_HUMAN:
            # 等待人工审核，不做规划
            return {
                "next_step": "wait_human",
                "reason": "等待人工审核确认",
            }

        # 正常流转：从当前状态到下一个
        return self._plan_next_step(current_status, state)

    def _plan_first_step(self, state: dict[str, Any]) -> dict[str, Any]:
        """首次启动规划"""
        return {
            "next_step": "molecule_agent",
            "next_status": JobStatus.PREPARING,
            "plan": [
                "molecule_agent",   # 1. 分子预处理
                "docking_agent",    # 2. Docking 筛选
                "ranking_agent",    # 3. 结果排序
                "analysis_agent",   # 4. AI 分析
                "report_agent",     # 5. 报告生成
            ],
            "message": "任务已创建，开始执行流程",
        }

    def _plan_next_step(self, current: JobStatus, state: dict[str, Any]) -> dict[str, Any]:
        """正常流程：根据当前状态确定下一步"""
        try:
            idx = self.FLOW_STEPS.index(current)
            if idx < len(self.FLOW_STEPS) - 1:
                next_status = self.FLOW_STEPS[idx + 1]
                next_agent = self.STATE_AGENT_MAP.get(next_status, "completed")
            else:
                next_status = JobStatus.COMPLETED
                next_agent = "completed"
        except ValueError:
            next_status = current
            next_agent = self.STATE_AGENT_MAP.get(current, "unknown")

        return {
            "next_step": next_agent,
            "next_status": next_status,
            "current_step": current,
        }

    def _plan_recovery(self, state: dict[str, Any]) -> dict[str, Any]:
        """从失败状态恢复"""
        last_agent = state.get("last_agent", "")
        failed_status = state.get("failed_at_status", JobStatus.PREPARING)

        return {
            "next_step": "retry",
            "next_status": JobStatus.RETRYING,
            "retry_target": self.STATE_AGENT_MAP.get(failed_status, "molecule_agent"),
            "retry_state": failed_status,
            "message": f"从 {failed_status} 恢复执行",
        }

    def _plan_retry(self, state: dict[str, Any]) -> dict[str, Any]:
        """重试规划"""
        retry_target = state.get("retry_target", "molecule_agent")
        retry_state = state.get("retry_state", JobStatus.PREPARING)

        return {
            "next_step": retry_target,
            "next_status": retry_state,
            "message": f"重试执行: {retry_target}",
        }
