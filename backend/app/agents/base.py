"""
Agent 基类

所有 Agent 继承 BaseAgent，提供统一的：
- 输入验证（validate_input）
- 执行流程（run / arun）
- 输出标准化（_format_output）
- 审计记录（_record_run）
"""

from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from app.core.constants import AgentStatus
from app.core.logger import get_logger


class AgentRunResult:
    """Agent 执行结果"""

    def __init__(
        self,
        agent_name: str,
        status: AgentStatus,
        output: dict[str, Any] = None,
        error: str = None,
        next_state: str = None,
        duration_ms: int = 0,
    ):
        self.agent_name = agent_name
        self.status = status
        self.output = output or {}
        self.error = error
        self.next_state = next_state
        self.duration_ms = duration_ms

    @classmethod
    def success(cls, agent_name: str, output: dict, next_state: str = None, duration_ms: int = 0) -> "AgentRunResult":
        return cls(agent_name=agent_name, status=AgentStatus.SUCCESS, output=output, next_state=next_state, duration_ms=duration_ms)

    @classmethod
    def failed(cls, agent_name: str, error: str, output: dict = None) -> "AgentRunResult":
        return cls(agent_name=agent_name, status=AgentStatus.FAILED, error=error, output=output or {})


class BaseAgent:
    """Agent 基类

    每个 Agent 子类实现:
    - name: Agent 名称标识
    - description: 功能描述
    - _validate_input(state): 输入验证
    - _execute(state): 核心执行逻辑
    - _format_output(result): 输出标准化
    """

    name: str = "base_agent"
    description: str = "基础 Agent"

    def __init__(self):
        self.logger = get_logger(f"agent.{self.name}")

    async def arun(self, state: dict[str, Any]) -> AgentRunResult:
        """异步执行 Agent（主入口）

        Args:
            state: LangGraph ScreeningState 字典

        Returns:
            AgentRunResult 包含执行状态和输出
        """
        import time
        start = time.perf_counter()

        try:
            # 1. 输入验证
            self._validate_input(state)
            self.logger.info(f"{self.name} 开始执行", job_id=state.get("task_id"))

            # 2. 执行核心逻辑
            output = await self._execute(state)

            # 3. 输出标准化
            formatted = self._format_output(output)

            duration_ms = int((time.perf_counter() - start) * 1000)
            self.logger.info(f"{self.name} 执行成功", duration_ms=duration_ms)

            return AgentRunResult.success(
                agent_name=self.name,
                output=formatted,
                next_state=self._next_state(state),
                duration_ms=duration_ms,
            )

        except Exception as e:
            self.logger.error(f"{self.name} 执行失败: {e}", exc_info=True)
            return AgentRunResult.failed(
                agent_name=self.name,
                error=str(e),
            )

    def _validate_input(self, state: dict[str, Any]) -> None:
        """验证输入 state 必需字段

        Args:
            state: ScreeningState 字典

        Raises:
            ValueError: 缺少必需字段
        """
        pass  # 子类按需覆写

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """核心执行逻辑（子类实现）"""
        raise NotImplementedError(f"{self.name}._execute 未实现")

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        """输出标准化（子类可覆写）"""
        return output

    def _next_state(self, state: dict[str, Any]) -> str:
        """确定下一个状态（子类可覆写）"""
        return state.get("job_status", "")
