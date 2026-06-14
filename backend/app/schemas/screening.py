"""
筛选任务相关 Pydantic 模型

请求：
- ScreeningCreateRequest: 创建筛选任务
- ScreeningListRequest: 任务列表查询

响应：
- ScreeningResponse: 任务详情
- ScreeningStatusResponse: 任务状态（轻量）
- TopHitsResponse: Top Hits 结果
- DockingTaskResponse: 单个 Docking 子任务
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求 ──


class ScreeningCreateRequest(BaseModel):
    """创建筛选任务请求

    用户提交一个 SMILES + 受体 ID 发起一次完整虚拟筛选。
    """
    project_id: int = Field(..., gt=0, description="项目 ID")
    smiles: Optional[str] = Field(None, min_length=1, max_length=4096, description="配体分子 SMILES 字符串")
    receptor_id: int = Field(..., gt=0, description="靶点受体 ID")
    job_name: Optional[str] = Field(None, min_length=1, max_length=255, description="任务名称（不提供则自动生成）")
    drug_db: Optional[str] = Field(None, description="药物数据库选择 (fda_approved/drugbank/custom)")
    exhaustiveness: Optional[int] = Field(None, ge=1, le=32, description="Vina 搜索详尽度")
    cpu_count: Optional[int] = Field(None, ge=1, le=64, description="CPU 核心数")
    top_n: Optional[int] = Field(None, ge=1, le=1000, description="返回 Top-N 结果数")


class ScreeningListRequest(BaseModel):
    """筛选任务列表查询"""
    project_id: Optional[int] = Field(None, description="按项目筛选")
    status: Optional[str] = Field(None, description="按状态筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class ScreeningCancelRequest(BaseModel):
    """取消任务请求"""
    reason: Optional[str] = Field(None, max_length=500, description="取消原因")


# ── 响应 ──


class ScreeningCreateResponse(BaseModel):
    """创建任务响应"""
    job_id: int
    job_name: str
    status: str
    message: str = "任务已创建，Agent 将自动开始处理"


class ScreeningStatusResponse(BaseModel):
    """任务状态响应（用于实时轮询）"""
    job_id: int
    job_name: str
    status: str
    progress: int = 0
    total_drugs: int = 0
    finished_drugs: int = 0
    created_at: Optional[str] = None


class ScreeningResponse(BaseModel):
    """任务完整详情"""
    id: int
    job_name: str
    project_id: int
    molecule_id: Optional[int] = None
    receptor_id: int
    status: str
    progress: int
    total_drugs: int
    finished_drugs: int
    created_by: int
    created_at: Optional[str] = None


class PaginatedScreeningResponse(BaseModel):
    """分页任务列表响应"""
    items: list[ScreeningResponse]
    total: int
    page: int
    page_size: int


class ScreeningStatsResponse(BaseModel):
    """任务统计响应"""
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int


class DockingTaskResponse(BaseModel):
    """Docking 子任务响应"""
    id: int
    job_id: int
    drug_id: int
    drug_name: Optional[str] = None
    affinity_score: Optional[float] = None
    status: str
    retry_count: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class TopHitItem(BaseModel):
    """Top Hit 条目"""
    rank: int
    drug_id: int
    drug_name: str
    smiles: Optional[str] = None
    affinity_score: float
    drugbank_id: Optional[str] = None


class TopHitsResponse(BaseModel):
    """Top Hits 结果响应"""
    job_id: int
    total_hits: int
    top_hits: list[TopHitItem]


class ScreeningProgressEvent(BaseModel):
    """SSE 推送的进度事件"""
    event: str = "progress"
    job_id: int
    status: str
    progress: int
    finished_drugs: int
    total_drugs: int
    message: Optional[str] = None
