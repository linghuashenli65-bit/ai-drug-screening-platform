"""
报告相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    """报告响应"""
    id: int
    job_id: int
    report_type: str
    report_uri: str
    generated_at: Optional[str] = None


class ReportDownloadResponse(BaseModel):
    """报告下载链接响应"""
    job_id: int
    report_type: str
    download_url: str
    expires_at: str


class AnalysisResultResponse(BaseModel):
    """AI 分析结果响应"""
    id: int
    job_id: int
    drug_id: int
    drug_name: Optional[str] = None
    llm_model: str
    summary: Optional[str] = None
    recommendation: Optional[str] = None
    risk_analysis: Optional[str] = None
    generated_at: Optional[str] = None


class InteractionResponse(BaseModel):
    """PLIP 相互作用响应"""
    id: int
    job_id: int
    drug_id: int
    hydrogen_bonds: int = 0
    hydrophobic_contacts: int = 0
    salt_bridges: int = 0
    pi_interactions: int = 0
    analysis_json: Optional[dict] = None
