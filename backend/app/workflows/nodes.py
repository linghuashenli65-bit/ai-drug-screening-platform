"""
LangGraph 工作流节点

每个节点封装一个 Agent 的执行。
节点函数签名: (ScreeningState) → dict (partial state update)
"""

from typing import Any

from app.agents.planner_agent import PlannerAgent
from app.agents.molecule_agent import MoleculeAgent
from app.agents.database_agent import DatabaseAgent
from app.agents.docking_agent import DockingAgent
from app.agents.ranking_agent import RankingAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.report_agent import ReportAgent
from app.core.constants import JobStatus
from app.core.logger import get_logger

logger = get_logger("workflow.nodes")


# 全局 Agent 单例
_planner = PlannerAgent()
_molecule = MoleculeAgent()
_database = DatabaseAgent()
_docking = DockingAgent()
_ranking = RankingAgent()
_analysis = AnalysisAgent()
_report = ReportAgent()


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Planner 节点：任务规划与路由决策

    根据当前状态决定下一步执行哪个 Agent。
    """
    logger.info(f"Planner 节点: task_id={state.get('task_id')}, status={state.get('job_status')}")
    result = await _planner.arun(state)

    return {
        "job_status": result.output.get("next_status", state.get("job_status")),
        "last_agent": "planner",
        "next_step": result.output.get("next_step", ""),
        "messages": [f"Planner: {result.output.get('message', '')}"],
    }


async def molecule_node(state: dict[str, Any]) -> dict[str, Any]:
    """Molecule 节点：分子预处理

    解析 SMILES → 计算描述符 → 3D 构象 → PDBQT 转换。
    """
    logger.info(f"Molecule 节点: task_id={state.get('task_id')}")
    result = await _molecule.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "molecule",
            "error_message": result.error or "分子预处理失败",
        }

    return {
        "job_status": JobStatus.DOCKING,
        "last_agent": "molecule",
        **result.output,
    }


async def database_node(state: dict[str, Any]) -> dict[str, Any]:
    """Database 节点：药物库加载

    从 MySQL 加载药物库，可选 Milvus 预筛选。
    """
    logger.info(f"Database 节点: task_id={state.get('task_id')}")
    result = await _database.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "database",
            "error_message": result.error or "药物库加载失败",
        }

    return {
        "last_agent": "database",
        **result.output,
    }


async def docking_node(state: dict[str, Any]) -> dict[str, Any]:
    """Docking 节点：任务拆分与入队

    将药物库拆分为子任务并推入 Redis Stream。
    """
    logger.info(f"Docking 节点: task_id={state.get('task_id')}")
    result = await _docking.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "docking",
            "error_message": result.error or "Docking 调度失败",
            **result.output,
        }

    return {
        "job_status": JobStatus.ANALYZING,
        "last_agent": "docking",
        **result.output,
    }


async def ranking_node(state: dict[str, Any]) -> dict[str, Any]:
    """Ranking 节点：结果排序

    按 Binding Affinity 排序，生成 Top-N 列表。
    """
    logger.info(f"Ranking 节点: task_id={state.get('task_id')}")
    result = await _ranking.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "ranking",
            "error_message": result.error or "结果排序失败",
        }

    return {
        "last_agent": "ranking",
        **result.output,
    }


async def analysis_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analysis 节点：AI 智能分析

    调用 LLM 对 Top Hits 进行多维度分析。
    """
    logger.info(f"Analysis 节点: task_id={state.get('task_id')}")
    result = await _analysis.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "analysis",
            "error_message": result.error or "AI 分析失败",
        }

    return {
        "job_status": JobStatus.REPORTING,
        "last_agent": "analysis",
        **result.output,
    }


async def report_node(state: dict[str, Any]) -> dict[str, Any]:
    """Report 节点：报告生成

    整合所有结果生成 PDF/Markdown/HTML 报告。
    """
    logger.info(f"Report 节点: task_id={state.get('task_id')}")
    result = await _report.arun(state)

    if result.status == "FAILED":
        return {
            "job_status": JobStatus.FAILED,
            "last_agent": "report",
            "error_message": result.error or "报告生成失败",
        }

    return {
        "job_status": JobStatus.COMPLETED,
        "last_agent": "report",
        **result.output,
    }


async def failed_node(state: dict[str, Any]) -> dict[str, Any]:
    """失败处理节点

    记录失败原因，判断是否需要重试。
    """
    error = state.get("error_message", "Unknown error")
    retry_count = state.get("retry_count", 0)
    max_retries = 3

    logger.warning(f"Failed 节点: task_id={state.get('task_id')}, error={error}, retry={retry_count}")

    if retry_count < max_retries:
        return {
            "job_status": JobStatus.RETRYING,
            "retry_count": retry_count + 1,
            "failed_at_status": state.get("job_status"),
            "last_agent": "failed_handler",
            "messages": [f"Failed: {error}, retrying ({retry_count + 1}/{max_retries})"],
        }

    return {
        "job_status": JobStatus.FAILED,
        "last_agent": "failed_handler",
        "messages": [f"Failed: {error}, max retries exceeded"],
    }


async def wait_human_node(state: dict[str, Any]) -> dict[str, Any]:
    """人工审核节点

    暂停工作流，等待科研人员确认后继续。
    """
    logger.info(f"WaitHuman 节点: task_id={state.get('task_id')}")
    return {
        "job_status": JobStatus.WAIT_HUMAN,
        "last_agent": "human_review",
        "messages": ["等待人工审核确认"],
    }
