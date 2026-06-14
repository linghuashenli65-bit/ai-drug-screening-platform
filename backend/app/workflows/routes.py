"""
LangGraph 条件路由

定义工作流中的条件分支：
- 正常路由：按状态机顺序流转
- 失败路由：检测 Agent 执行失败，进入重试或人工审核
- 人工审核路由：低置信度或高风险时暂停等待确认
"""

from typing import Any, Literal

from app.core.constants import JobStatus

# 节点名称类型
NodeName = Literal[
    "planner",
    "molecule",
    "database",
    "docking",
    "ranking",
    "analysis",
    "report",
    "failed",
    "wait_human",
    "__end__",
]


def route_after_planner(state: dict[str, Any]) -> NodeName:
    """Planner 之后的路径选择

    根据 Planner 输出的 next_step 决定下一个节点。
    """
    next_step = state.get("next_step", "")

    route_map = {
        "molecule_agent": "molecule",
        "docking_agent": "docking",
        "analysis_agent": "analysis",
        "report_agent": "report",
        "completed": "__end__",
        "retry": "molecule",  # 默认从 molecule 开始重试
        "wait_human": "wait_human",
    }

    return route_map.get(next_step, "molecule")


def route_after_molecule(state: dict[str, Any]) -> NodeName:
    """Molecule 之后的路径选择

    分子准备完成后，检查是否有错误。成功则流向 database。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"
    return "database"


def route_after_database(state: dict[str, Any]) -> NodeName:
    """Database 之后的路径选择

    药物库加载完成后进入 Docking。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"

    drug_list = state.get("drug_list", [])
    if not drug_list:
        return "failed"  # 药物库为空

    return "docking"


def route_after_docking(state: dict[str, Any]) -> NodeName:
    """Docking 之后的路径选择

    Docking 执行完成后进入排序。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"
    return "ranking"


def route_after_ranking(state: dict[str, Any]) -> NodeName:
    """Ranking 之后的路径选择

    排序完成后进入 AI 分析。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"
    return "analysis"


def route_after_analysis(state: dict[str, Any]) -> NodeName:
    """Analysis 之后的路径选择

    AI 分析完成后进入报告生成。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"
    return "report"


def route_after_report(state: dict[str, Any]) -> NodeName:
    """Report 之后的路径选择

    报告生成完成后结束。如有问题可触发人工审核。
    """
    if state.get("job_status") == JobStatus.FAILED:
        return "failed"
    if state.get("job_status") == JobStatus.WAIT_HUMAN:
        return "wait_human"
    return "__end__"


def route_after_failed(state: dict[str, Any]) -> NodeName:
    """失败处理后的路径选择

    - RETRYING: 从 Planner 重新开始
    - FAILED: 终止
    - WAIT_HUMAN: 等待人工审核
    """
    job_status = state.get("job_status", "")

    if job_status == JobStatus.RETRYING:
        return "planner"
    if job_status == JobStatus.WAIT_HUMAN:
        return "wait_human"
    return "__end__"  # FAILED or CANCELLED → 终止
