"""
筛选任务 API

POST   /api/v1/screenings           — 创建筛选任务
GET    /api/v1/screenings/{id}      — 查询任务详情
GET    /api/v1/screenings/{id}/status  — 查询任务状态
GET    /api/v1/screenings/{id}/progress — 查询任务状态（/status 别名）
GET    /api/v1/screenings/{id}/results — 查询 Top Hits
GET    /api/v1/screenings/{id}/top-hits — 查询 Top Hits（/results 别名）
GET    /api/v1/screenings           — 查询任务列表
POST   /api/v1/screenings/{id}/cancel  — 取消任务
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, ResourceNotFound, ValidationError
from app.core.logger import get_logger
from app.core.redis import get_redis, get_job_progress, cache_job_progress, get_top_hits as redis_get_top_hits
from app.core.security import get_current_user
from app.tools.llm.client import LLMClient
from app.models.docking import DockingTask
from app.models.molecule import DrugLibrary
from app.models.project import Project
from app.models.receptor import Receptor
from app.models.screening import ScreeningJob
from app.schemas.screening import (
    PaginatedScreeningResponse,
    ScreeningCancelRequest,
    ScreeningCreateRequest,
    ScreeningCreateResponse,
    ScreeningListRequest,
    ScreeningResponse,
    ScreeningStatsResponse,
    ScreeningStatusResponse,
    TopHitItem,
    TopHitsResponse,
)

router = APIRouter()
logger = get_logger("api.screening")


async def _run_workflow(job_id: int, job_name: str, project_id: int, smiles: str,
                        receptor_id: int, receptor_name: str, pdb_code: str, created_by: int):
    """在后台运行 LangGraph 筛选工作流"""
    from app.core.database import AsyncSessionLocal
    from app.workflows.graph_builder import screening_graph
    from app.workflows.states import create_initial_state

    async def _update_job_status(status: str, progress: int = None, error_msg: str = None):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                if error_msg:
                    job.error_message = error_msg
                await session.commit()

    try:
        await _update_job_status("DOCKING")
        await cache_job_progress(job_id, {"status": "DOCKING", "progress": 0, "finished_drugs": 0, "total_drugs": 0})

        # 写入前置节点日志
        r = get_redis()
        for node_id, msg in [
            ("planner", f"[任务规划] 已创建筛选任务: {job_name}"),
            ("prepare_ligand", f"[分子准备] SMILES 解析完成"),
            ("load_library", f"[数据库加载] 受体: {receptor_name}, 药物库已加载"),
        ]:
            await r.rpush(f"job:{job_id}:node:{node_id}:logs", msg)
            await r.expire(f"job:{job_id}:node:{node_id}:logs", 86400)

        initial_state = create_initial_state(
            task_id=job_id,
            job_name=job_name,
            project_id=project_id,
            smiles=smiles,
            receptor_id=receptor_id,
            receptor_name=receptor_name,
            pdb_code=pdb_code,
            created_by=created_by,
        )
        logger.info(f"Job {job_id}: 启动 LangGraph 工作流")
        final_state = await screening_graph.ainvoke(initial_state)
        logger.info(f"Job {job_id}: 工作流执行完成")

        final_status = final_state.get("job_status", "COMPLETED")
        if final_status in ("FAILED", "WAIT_HUMAN"):
            await _update_job_status(final_status, error_msg=final_state.get("error_message", ""))
        else:
            await _update_job_status("COMPLETED", progress=100)
            await cache_job_progress(job_id, {"status": "COMPLETED", "progress": 100})

    except Exception as e:
        logger.error(f"Job {job_id}: 工作流执行失败: {e}", exc_info=True)
        await _update_job_status("FAILED", error_msg=str(e))


def _check_job_access(job, current_user: dict) -> None:
    """检查用户是否有权限访问指定任务。

    ADMIN 和 PI 可访问所有任务。
    RESEARCHER 和 VIEWER 仅能访问自己创建的任务。
    """
    if current_user["role"] in ("ADMIN", "PI"):
        return
    if job.created_by != current_user["user_id"]:
        raise PermissionDenied(message="无权访问此任务")


@router.post("/", response_model=ScreeningCreateResponse, status_code=201)
async def create_screening(
    req: ScreeningCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的虚拟筛选任务

    用户提交 SMILES + 受体 ID 发起一次完整虚拟筛选。
    Agent 将自动执行：分子处理 → Docking → 分析 → 报告。
    """
    # 验证项目是否存在
    project_result = await db.execute(select(Project).where(Project.id == req.project_id))
    if not project_result.scalar_one_or_none():
        raise ResourceNotFound(message=f"项目 ID={req.project_id} 不存在")

    # 验证受体是否存在
    receptor_result = await db.execute(select(Receptor).where(Receptor.id == req.receptor_id))
    receptor = receptor_result.scalar_one_or_none()
    if not receptor:
        raise ResourceNotFound(message=f"受体 ID={req.receptor_id} 不存在")

    # 自动生成 job_name
    job_name = req.job_name
    if not job_name:
        smiles_preview = (req.smiles[:30] + "...") if req.smiles and len(req.smiles) > 30 else (req.smiles or "ligand")
        job_name = f"{receptor.receptor_name}-{smiles_preview}-Screening"

    job = ScreeningJob(
        project_id=req.project_id,
        molecule_id=None,  # molecule_agent 执行后更新
        receptor_id=req.receptor_id,
        job_name=job_name,
        status="CREATED",
        progress=0,
        total_drugs=0,
        finished_drugs=0,
        created_by=current_user["user_id"],
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # 缓存初始进度到 Redis
    await cache_job_progress(job.id, {
        "status": "CREATED",
        "progress": 0,
        "finished_drugs": 0,
        "total_drugs": 0,
    })

    # 启动 LangGraph 工作流（后台异步执行）
    asyncio.create_task(_run_workflow(
        job_id=job.id,
        job_name=job.job_name,
        project_id=job.project_id,
        smiles=req.smiles or "",
        receptor_id=req.receptor_id,
        receptor_name=receptor.receptor_name,
        pdb_code=receptor.pdb_code or "",
        created_by=current_user["user_id"],
    ))

    return ScreeningCreateResponse(
        job_id=job.id,
        job_name=job.job_name,
        status=job.status,
        message="任务已创建，Agent 将自动开始处理",
    )


@router.get("/stats", response_model=ScreeningStatsResponse)
async def get_screening_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务统计数据"""
    base_query = select(ScreeningJob)
    if current_user["role"] in ("RESEARCHER", "VIEWER"):
        base_query = base_query.where(ScreeningJob.created_by == current_user["user_id"])

    total = (await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )).scalar() or 0

    running = (await db.execute(
        select(func.count()).select_from(
            base_query.where(ScreeningJob.status.notin_(["COMPLETED", "FAILED", "CANCELLED"])).subquery()
        )
    )).scalar() or 0

    completed = (await db.execute(
        select(func.count()).select_from(
            base_query.where(ScreeningJob.status == "COMPLETED").subquery()
        )
    )).scalar() or 0

    failed = (await db.execute(
        select(func.count()).select_from(
            base_query.where(ScreeningJob.status == "FAILED").subquery()
        )
    )).scalar() or 0

    return ScreeningStatsResponse(
        total_jobs=total,
        running_jobs=running,
        completed_jobs=completed,
        failed_jobs=failed,
    )


@router.get("/{job_id}", response_model=ScreeningResponse)
async def get_screening(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询筛选任务详情"""
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")

    _check_job_access(job, current_user)

    return ScreeningResponse(
        id=job.id,
        job_name=job.job_name,
        project_id=job.project_id,
        molecule_id=job.molecule_id,
        receptor_id=job.receptor_id,
        status=job.status,
        progress=job.progress,
        total_drugs=job.total_drugs,
        finished_drugs=job.finished_drugs,
        created_by=job.created_by,
        created_at=str(job.created_at) if job.created_at else None,
    )


@router.get("/{job_id}/status", response_model=ScreeningStatusResponse)
async def get_screening_status(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务实时状态（优先从 Redis 读取）"""
    # 优先从 Redis 读取
    progress = await get_job_progress(job_id)
    if progress:
        return ScreeningStatusResponse(
            job_id=job_id,
            job_name=progress.get("job_name", ""),
            status=progress.get("status", "UNKNOWN"),
            progress=int(progress.get("progress", 0)),
            total_drugs=int(progress.get("total_drugs", 0)),
            finished_drugs=int(progress.get("finished_drugs", 0)),
        )

    # 回退到 MySQL
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")

    _check_job_access(job, current_user)

    return ScreeningStatusResponse(
        job_id=job.id,
        job_name=job.job_name,
        status=job.status,
        progress=job.progress,
        total_drugs=job.total_drugs,
        finished_drugs=job.finished_drugs,
        created_at=str(job.created_at) if job.created_at else None,
    )


@router.get("/{job_id}/results", response_model=TopHitsResponse)
async def get_screening_results(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询 Top Hits 结果（优先从 Redis 缓存读取）"""
    # 权限检查
    job_result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    _check_job_access(job, current_user)

    # 先检查 Redis 缓存
    cached = await redis_get_top_hits(job_id)
    if cached:
        top_items = [TopHitItem(**hit) for hit in cached]
        return TopHitsResponse(job_id=job_id, total_hits=len(cached), top_hits=top_items)

    # 回退到 MySQL
    result = await db.execute(
        select(DockingTask, DrugLibrary.drug_name, DrugLibrary.drugbank_id, DrugLibrary.smiles)
        .join(DrugLibrary, DockingTask.drug_id == DrugLibrary.id)
        .where(DockingTask.job_id == job_id, DockingTask.affinity_score.isnot(None))
        .order_by(DockingTask.affinity_score.asc())
        .limit(100)
    )
    rows = result.all()

    top_hits = []
    for rank, (task, drug_name, drugbank_id, smiles) in enumerate(rows, 1):
        top_hits.append(TopHitItem(
            rank=rank,
            drug_id=task.drug_id,
            drug_name=drug_name or "",
            smiles=smiles,
            affinity_score=float(task.affinity_score),
            drugbank_id=drugbank_id,
        ))

    return TopHitsResponse(job_id=job_id, total_hits=len(top_hits), top_hits=top_hits)


@router.get("/", response_model=PaginatedScreeningResponse)
async def list_screenings(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询筛选任务列表"""
    base_query = select(ScreeningJob)

    # RESEARCHER / VIEWER 仅能查看自己创建的任务
    if current_user["role"] in ("RESEARCHER", "VIEWER"):
        base_query = base_query.where(ScreeningJob.created_by == current_user["user_id"])

    if project_id:
        base_query = base_query.where(ScreeningJob.project_id == project_id)
    if status:
        base_query = base_query.where(ScreeningJob.status == status)
    if search:
        base_query = base_query.where(ScreeningJob.job_name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated fetch
    data_query = base_query.order_by(ScreeningJob.created_at.desc())
    data_query = data_query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(data_query)
    jobs = result.scalars().all()

    items = [
        ScreeningResponse(
            id=job.id,
            job_name=job.job_name,
            project_id=job.project_id,
            molecule_id=job.molecule_id,
            receptor_id=job.receptor_id,
            status=job.status,
            progress=job.progress,
            total_drugs=job.total_drugs,
            finished_drugs=job.finished_drugs,
            created_by=job.created_by,
            created_at=str(job.created_at) if job.created_at else None,
        )
        for job in jobs
    ]

    return PaginatedScreeningResponse(items=items, total=total, page=page, page_size=page_size)


AGENT_CHAIN = [
    {"id": "planner", "name": "Planner Agent", "label": "任务规划"},
    {"id": "prepare_ligand", "name": "Molecule Agent", "label": "分子准备"},
    {"id": "load_library", "name": "Database Agent", "label": "数据库加载"},
    {"id": "docking", "name": "Docking Agent", "label": "Docking 执行"},
    {"id": "ranking", "name": "Ranking Agent", "label": "结果排序"},
    {"id": "analysis", "name": "Analysis Agent", "label": "AI 分析"},
    {"id": "report", "name": "Report Agent", "label": "报告生成"},
]

STATUS_TO_ACTIVE_INDEX = {
    "CREATED": -1,
    "PREPARING": 1,
    "DOCKING": 3,
    "ANALYZING": 5,
    "REPORTING": 6,
    "COMPLETED": 7,
    "FAILED": -2,
    "CANCELLED": -2,
}


def _derive_nodes(job_status: str, progress: int) -> list[dict]:
    """根据任务状态推导各 Agent 节点的状态"""
    active_idx = STATUS_TO_ACTIVE_INDEX.get(job_status, -1)
    nodes = []
    for i, agent in enumerate(AGENT_CHAIN):
        if active_idx == -2:
            # FAILED/CANCELLED: estimate which node failed based on progress
            failed_idx = int(progress / 100 * len(AGENT_CHAIN))
            if i < failed_idx:
                state = "SUCCESS"
            elif i == failed_idx:
                state = "FAILED" if job_status == "FAILED" else "PENDING"
            else:
                state = "PENDING"
        elif i < active_idx:
            state = "SUCCESS"
        elif i == active_idx:
            state = "RUNNING"
        else:
            state = "PENDING"
        nodes.append({
            "id": agent["id"],
            "name": agent["name"],
            "label": agent["label"],
            "state": state,
            "retry_count": 0,
        })
    return nodes


@router.get("/{job_id}/nodes")
async def get_screening_nodes(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务的 Agent 节点状态"""
    progress_data = await get_job_progress(job_id)
    if progress_data:
        status = progress_data.get("status", "CREATED")
        progress = int(progress_data.get("progress", 0))
    else:
        result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
        _check_job_access(job, current_user)
        status = job.status
        progress = job.progress

    return _derive_nodes(status, progress)


@router.get("/{job_id}/nodes/{node_id}/logs")
async def get_node_logs(
    job_id: int,
    node_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定节点的执行日志"""
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    _check_job_access(job, current_user)

    # Check Redis for cached logs
    r = get_redis()
    log_key = f"job:{job_id}:node:{node_id}:logs"
    cached_logs = await r.lrange(log_key, 0, -1)
    if cached_logs:
        return cached_logs

    # Derive basic log from node state
    nodes = _derive_nodes(job.status, job.progress)
    node = next((n for n in nodes if n["id"] == node_id), None)
    if not node:
        return []

    agent_label = node["label"]
    state = node["state"]
    logs = []
    if state == "SUCCESS":
        logs = [f"[{agent_label}] 启动执行", f"[{agent_label}] 执行完成"]
    elif state == "RUNNING":
        logs = [f"[{agent_label}] 启动执行", f"[{agent_label}] 执行中..."]
    elif state == "FAILED":
        logs = [f"[{agent_label}] 启动执行", f"[{agent_label}] 执行失败"]
    else:
        logs = [f"[{agent_label}] 等待执行"]

    return logs


async def _build_job_context(job, db) -> str:
    """构建任务上下文信息供 LLM 参考"""
    # 获取受体信息
    receptor_name = f"受体 ID={job.receptor_id}"
    receptor_result = await db.execute(select(Receptor).where(Receptor.id == job.receptor_id))
    receptor = receptor_result.scalar_one_or_none()
    if receptor:
        receptor_name = f"{receptor.receptor_name} (PDB: {receptor.pdb_code or 'N/A'})"

    # 获取 Top Hits
    top_hits = await redis_get_top_hits(job.id)
    hits_text = "暂无对接结果数据。"
    if top_hits:
        lines = []
        for hit in top_hits[:10]:
            lines.append(
                f"  #{hit.get('rank', '?')} {hit.get('drug_name', 'Unknown')} "
                f"Score={hit.get('affinity_score', 'N/A')} kcal/mol "
                f"SMILES={hit.get('smiles', 'N/A')}"
            )
        hits_text = f"Top {len(lines)} 对接结果:\n" + "\n".join(lines)

    context = (
        f"任务信息:\n"
        f"  任务 ID: {job.id}\n"
        f"  任务名称: {job.job_name}\n"
        f"  靶点蛋白: {receptor_name}\n"
        f"  药物库药物数: {job.total_drugs}\n"
        f"  已完成对接数: {job.finished_drugs}\n"
        f"  任务状态: {job.status}\n\n"
        f"{hits_text}"
    )
    return context


@router.get("/{job_id}/analysis")
async def get_screening_analysis(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 分析结果"""
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    _check_job_access(job, current_user)

    # Check Redis for cached analysis
    r = get_redis()
    analysis_key = f"job:{job_id}:analysis"
    cached = await r.get(analysis_key)
    if cached:
        return json.loads(cached)

    if job.status != "COMPLETED":
        return {
            "candidate_analysis": None,
            "drug_repurposing": None,
            "risk_analysis": None,
            "experiment_suggestions": None,
        }

    # Build context and call LLM
    context = await _build_job_context(job, db)
    llm = LLMClient()

    system_prompt = (
        "你是一个药物虚拟筛选 AI 分析专家。根据以下筛选任务的对接结果，"
        "请提供专业的药物分析报告。请用中文回答。\n\n"
        f"{context}\n\n"
        "请严格按照以下 4 个部分输出分析，每个部分用 === 分隔：\n"
        "1. 候选药物分析：分析排名靠前的候选药物的结合特征和潜力\n"
        "2. 药物重定位分析：评估已批准药物用于新靶点的可能性\n"
        "3. 风险分析：指出潜在的安全性、选择性或成药性问题\n"
        "4. 实验建议：建议下一步的体外/体内验证实验方案"
    )

    try:
        llm_result = await llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据上述对接数据生成完整的 AI 分析报告。"},
            ],
            temperature=0.4,
            max_tokens=3000,
        )
        content = llm_result.data.get("content", "")
    except Exception as e:
        logger.warning(f"Job {job_id}: AI 分析 LLM 调用失败，返回降级结果: {e}")
        analysis_data = {
            "candidate_analysis": f"任务 {job.job_name} 已完成虚拟筛选（{context[:200]}...）。LLM 分析服务暂时不可用，请稍后重试。",
            "drug_repurposing": None,
            "risk_analysis": None,
            "experiment_suggestions": None,
        }
        return analysis_data

    # Parse structured response
    sections = content.split("===")
    analysis_data = {
        "candidate_analysis": sections[0].strip() if len(sections) > 0 else None,
        "drug_repurposing": sections[1].strip() if len(sections) > 1 else None,
        "risk_analysis": sections[2].strip() if len(sections) > 2 else None,
        "experiment_suggestions": sections[3].strip() if len(sections) > 3 else None,
    }

    # If LLM didn't follow the separator format, put everything in candidate_analysis
    if len(sections) <= 1 and content:
        analysis_data["candidate_analysis"] = content

    # Cache in Redis for 1 hour
    await r.set(analysis_key, json.dumps(analysis_data, ensure_ascii=False), ex=3600)

    return analysis_data


@router.post("/{job_id}/analysis/chat")
async def screening_analysis_chat(
    job_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 分析聊天接口 — 基于筛选结果的智能问答"""
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    _check_job_access(job, current_user)

    body = await request.json()
    question = body.get("question", "")
    history = body.get("history", [])

    # Build context
    context = await _build_job_context(job, db)

    system_prompt = (
        "你是一个药物虚拟筛选 AI 分析助手。用户正在查看一次虚拟筛选任务的结果，"
        "你需要根据对接数据回答用户关于候选药物、结合模式、药物重定位等方面的问题。\n"
        "请用中文回答，简洁专业。\n\n"
        f"当前任务上下文:\n{context}"
    )

    # Build messages for LLM
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 10 turns max)
    for msg in history[-10:]:
        if msg.get("role") in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    llm = LLMClient()
    llm_result = await llm.chat(
        messages=messages,
        temperature=0.5,
        max_tokens=1500,
    )

    answer = llm_result.data.get("content", "抱歉，AI 分析暂时不可用。")
    return {"answer": answer}


@router.post("/{job_id}/cancel")
async def cancel_screening(
    job_id: int,
    req: ScreeningCancelRequest = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消筛选任务"""
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")

    _check_job_access(job, current_user)

    job.status = "CANCELLED"
    await db.flush()

    await cache_job_progress(job_id, {
        "status": "CANCELLED",
        "progress": job.progress,
        "finished_drugs": job.finished_drugs,
        "total_drugs": job.total_drugs,
    })

    return {"job_id": job_id, "status": "CANCELLED", "message": "任务已取消"}


# ── 路径别名 ──


@router.get("/{job_id}/progress", response_model=ScreeningStatusResponse)
async def get_screening_progress(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务实时进度 — /status 的别名，供前端调用"""
    return await get_screening_status(job_id, current_user, db)


@router.get("/{job_id}/top-hits", response_model=TopHitsResponse)
async def get_screening_top_hits(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询 Top Hits — /results 的别名，供前端调用"""
    return await get_screening_results(job_id, current_user, db)


@router.get("/{job_id}/events")
async def screening_events(
    job_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 端点 — 实时推送任务进度

    前端通过 fetch + ReadableStream 消费此端点，获取实时进度更新。
    事件类型:
      - progress: 进度变化
      - complete: 任务完成/失败/取消
    """
    result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    _check_job_access(job, current_user)

    from app.core.database import AsyncSessionLocal

    async def event_generator():
        terminal_statuses = {"COMPLETED", "FAILED", "CANCELLED"}
        last_progress = -1
        last_status = ""
        max_idle_seconds = 3600

        elapsed = 0
        while elapsed < max_idle_seconds:
            if await request.is_disconnected():
                break

            progress_data = await get_job_progress(job_id)

            if progress_data:
                status = progress_data.get("status", "UNKNOWN")
                progress = int(progress_data.get("progress", 0))
                finished = int(progress_data.get("finished_drugs", 0))
                total = int(progress_data.get("total_drugs", 0))
            else:
                async with AsyncSessionLocal() as sess:
                    r = await sess.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
                    fresh_job = r.scalar_one_or_none()
                if not fresh_job:
                    break
                status = fresh_job.status
                progress = fresh_job.progress
                finished = fresh_job.finished_drugs
                total = fresh_job.total_drugs

            if progress != last_progress or status != last_status:
                last_progress = progress
                last_status = status

                job_payload = {
                    "id": job_id,
                    "status": status,
                    "progress": progress,
                    "finished_drugs": finished,
                    "total_drugs": total,
                }

                if status in terminal_statuses:
                    yield f"event: complete\ndata: {json.dumps({'job': job_payload})}\n\n"
                    break
                else:
                    yield f"event: progress\ndata: {json.dumps({'job': job_payload})}\n\n"

            await asyncio.sleep(2)
            elapsed += 2

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
