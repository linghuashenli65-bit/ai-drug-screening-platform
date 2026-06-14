"""
ScreeningState — LangGraph 工作流状态定义

状态机设计：
  CREATED → PREPARING → DOCKING → ANALYZING → REPORTING → COMPLETED
  任意状态 → FAILED | CANCELLED | WAIT_HUMAN
  FAILED → RETRYING → (回到前一状态)

State 只放必要字段（IDs/URIs/状态），大文件内容存 MinIO。
"""

from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


class ScreeningState(TypedDict):
    """虚拟筛选工作流全局状态

    此 TypedDict 在 LangGraph 各节点间传递。
    每个节点读取所需字段，写入输出字段。"""

    # ── 任务标识 ──
    task_id: int                     # 筛选任务 ID (screening_jobs.id)
    job_name: str                    # 任务名称
    project_id: int                  # 项目 ID
    created_by: int                  # 创建用户 ID

    # ── 输入 ──
    smiles: str                     # 配体分子 SMILES
    input_file: str                 # 输入文件路径（SDF/MOL2 等）
    receptor_id: int                # 靶点受体 ID
    receptor_name: str              # 靶点受体名称
    pdb_code: str                   # 受体 PDB 代码

    # ── 状态控制 ──
    job_status: str                 # 当前业务状态 (JobStatus)
    last_agent: str                 # 上一个执行的 Agent
    error_message: str              # 错误信息
    retry_count: int                # 重试次数
    failed_at_status: str           # 失败时的业务状态（用于恢复）

    # ── 分子准备 ──
    ligand_sdf_path: str            # 配体 3D 构象 SDF 文件路径
    ligand_pdbqt_path: str          # 配体 PDBQT 文件路径
    fingerprint: list[int]          # Morgan 指纹向量 (2048 位)
    descriptors: dict[str, Any]     # 分子描述符

    # ── 药物库 ──
    drug_list: list[dict]           # 候选药物列表 [{drug_id, drug_name, pdbqt_uri, ...}]
    total_drugs: int                # 药物库总数
    use_milvus_prescreen: bool      # 是否使用 Milvus 预筛选
    prescreen_top_k: int            # 预筛选 Top-K

    # ── Docking ──
    docking_tasks: list[dict]       # Docking 子任务列表
    docking_results: list[dict]     # Docking 结果列表
    top_n: int                      # Top-N 数量
    total_docked: int               # 已完成对接数

    # ── 排序与分析 ──
    top_hits: list[dict]            # Top Hits 列表 (含 rank, score, drug_name)
    statistics: dict[str, Any]      # 统计信息 (mean, median, quartiles)
    overall_analysis: str           # AI 总体分析文本
    top_drug_analyses: list[dict]   # Top 药物详细分析
    analysis_top_n: int             # 分析 Top-N (默认 3)
    report_summary: str             # 报告摘要

    # ── 报告 ──
    report_uri: str                 # 报告 MinIO URI
    report_type: str                # 报告格式
    report_format: str              # 请求的报告格式

    # ── LangGraph 消息 ──
    messages: Annotated[list, add_messages]  # 消息历史（用于 LLM 对话）


def create_initial_state(
    task_id: int,
    job_name: str,
    project_id: int,
    smiles: str,
    receptor_id: int,
    receptor_name: str = "",
    pdb_code: str = "",
    created_by: int = 0,
    **kwargs,
) -> ScreeningState:
    """创建初始工作流状态

    Args:
        task_id: 筛选任务 ID
        job_name: 任务名称
        project_id: 项目 ID
        smiles: 配体分子 SMILES
        receptor_id: 受体 ID
        receptor_name: 受体名称
        pdb_code: PDB 代码
        created_by: 创建者
        **kwargs: 其他可选状态字段

    Returns:
        初始化的 ScreeningState
    """
    return ScreeningState(
        task_id=task_id,
        job_name=job_name,
        project_id=project_id,
        smiles=smiles,
        receptor_id=receptor_id,
        receptor_name=receptor_name,
        pdb_code=pdb_code,
        created_by=created_by,
        job_status="CREATED",
        last_agent="",
        error_message="",
        retry_count=0,
        failed_at_status="",
        ligand_sdf_path="",
        ligand_pdbqt_path="",
        fingerprint=[],
        descriptors={},
        drug_list=[],
        total_drugs=0,
        use_milvus_prescreen=True,
        prescreen_top_k=1000,
        docking_tasks=[],
        docking_results=[],
        top_n=100,
        total_docked=0,
        top_hits=[],
        statistics={},
        overall_analysis="",
        top_drug_analyses=[],
        analysis_top_n=3,
        report_summary="",
        report_uri="",
        report_type="",
        report_format=kwargs.get("report_format", "pdf"),
        messages=[],
    )
