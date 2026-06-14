"""
分析结果模型 (interaction_analyses, ai_analysis_results)

interaction_analyses: PLIP 蛋白-配体相互作用分析结果
ai_analysis_results: LLM 生成的药物分析与推荐
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InteractionAnalysis(Base):
    """蛋白-配体相互作用分析 (PLIP)

    存储 PLIP 工具分析的结果，包括氢键、疏水接触、盐桥、pi-pi 等相互作用。
    """

    __tablename__ = "interaction_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("screening_jobs.id"), nullable=False, index=True)
    drug_id: Mapped[int] = mapped_column(Integer, nullable=False)
    hydrogen_bonds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hydrophobic_contacts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    salt_bridges: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pi_interactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_json: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 关系
    job: Mapped["ScreeningJob"] = relationship("ScreeningJob", back_populates="interaction_analyses", lazy="selectin")


class AIAnalysisResult(Base):
    """AI/LLM 分析结果

    存储 LLM 对 Docking 结果的智能分析和推荐建议。
    包括：结合能力评价、药物重定位潜力、风险评估、实验建议。
    """

    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("screening_jobs.id"), nullable=False, index=True)
    drug_id: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_model: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str] = mapped_column(Text, nullable=True)
    risk_analysis: Mapped[str] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    job: Mapped["ScreeningJob"] = relationship("ScreeningJob", back_populates="ai_analysis_results", lazy="selectin")
