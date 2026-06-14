"""
LangGraph 工作流构建器

构建完整的虚拟筛选 LangGraph 状态图：
1. 定义所有节点
2. 定义边和条件路由
3. 设置入口点和终止点

图结构:
    START → planner → molecule → database → docking → ranking → analysis → report → END
                                ↑                    ↓          ↓         ↓
                                └──── failed_node ───┴──────────┴─────────┘
                                          ↓
                                     wait_human
"""

from langgraph.graph import END, START, StateGraph

from app.workflows.nodes import (
    analysis_node,
    database_node,
    docking_node,
    failed_node,
    molecule_node,
    planner_node,
    ranking_node,
    report_node,
    wait_human_node,
)
from app.workflows.routes import (
    route_after_analysis,
    route_after_database,
    route_after_docking,
    route_after_failed,
    route_after_molecule,
    route_after_planner,
    route_after_ranking,
    route_after_report,
)
from app.workflows.states import ScreeningState


def build_screening_graph() -> StateGraph:
    """构建筛选工作流 LangGraph 图

    节点:
        planner - 任务规划与路由
        molecule - 分子预处理
        database - 药物库加载
        docking - 分子对接调度
        ranking - 结果排序
        analysis - AI 分析
        report - 报告生成
        failed - 失败处理
        wait_human - 人工审核

    Returns:
        编译好的 StateGraph (可执行)
    """
    # 创建状态图
    workflow = StateGraph(ScreeningState)

    # 注册节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("molecule", molecule_node)
    workflow.add_node("database", database_node)
    workflow.add_node("docking", docking_node)
    workflow.add_node("ranking", ranking_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("report", report_node)
    workflow.add_node("failed", failed_node)
    workflow.add_node("wait_human", wait_human_node)

    # ── 边定义 ──

    # START → planner
    workflow.add_edge(START, "planner")

    # planner → 条件路由 (molecule / __end__ / wait_human / retry)
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "molecule": "molecule",
            "docking": "docking",
            "analysis": "analysis",
            "report": "report",
            "__end__": END,
            "failed": "failed",
            "wait_human": "wait_human",
        },
    )

    # molecule → database (正常) / failed (异常)
    workflow.add_conditional_edges(
        "molecule",
        route_after_molecule,
        {"database": "database", "failed": "failed"},
    )

    # database → docking / failed
    workflow.add_conditional_edges(
        "database",
        route_after_database,
        {"docking": "docking", "failed": "failed"},
    )

    # docking → ranking / failed
    workflow.add_conditional_edges(
        "docking",
        route_after_docking,
        {"ranking": "ranking", "failed": "failed"},
    )

    # ranking → analysis / failed
    workflow.add_conditional_edges(
        "ranking",
        route_after_ranking,
        {"analysis": "analysis", "failed": "failed"},
    )

    # analysis → report / failed
    workflow.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {"report": "report", "failed": "failed"},
    )

    # report → END / failed / wait_human
    workflow.add_conditional_edges(
        "report",
        route_after_report,
        {"__end__": END, "failed": "failed", "wait_human": "wait_human"},
    )

    # failed → planner(重试) / __end__ / wait_human
    workflow.add_conditional_edges(
        "failed",
        route_after_failed,
        {"planner": "planner", "__end__": END, "wait_human": "wait_human"},
    )

    # wait_human → END (等待人工操作后从外部恢复)
    workflow.add_edge("wait_human", END)

    # 编译
    compiled_graph = workflow.compile()
    return compiled_graph


# 全局图实例
screening_graph = build_screening_graph()
