"""
Agent 运行记录模型 (agent_runs, tool_calls)

agent_runs: LangGraph/Agent 运行审计，用于监控和调试
tool_calls: Agent Tool 调用记录，用于审计追踪
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, Integer, String, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AgentRun(Base):
    """Agent 运行轨迹

    记录每个 Agent 的执行过程，用于：
    - LangGraph 监控
    - Agent 调试
    - 审计追踪
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("screening_jobs.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    state_before: Mapped[str] = mapped_column(String(64), nullable=True)
    state_after: Mapped[str] = mapped_column(String(64), nullable=True)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    job: Mapped["ScreeningJob"] = relationship("ScreeningJob", back_populates="agent_runs", lazy="selectin")
    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="agent_run", lazy="selectin")


class ToolCall(Base):
    """Agent Tool 调用记录

    记录每次 Tool 调用的输入、输出、耗时和状态。
    用于 Agent 可观测性和审计。
    """

    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")

    # 关系
    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls", lazy="selectin")
