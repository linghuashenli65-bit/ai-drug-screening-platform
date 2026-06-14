"""
Tool 基类定义

所有 Tool 继承 BaseTool，遵循统一接口：
- name: Tool 名称标识
- description: 功能描述
- 返回 ToolResult（包含 data, success, error）
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """Tool 执行结果

    Attributes:
        success: 是否成功
        data: 返回数据
        error: 错误信息（失败时）
        tool_name: Tool 名称
        duration_ms: 执行耗时 (ms)
    """

    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    tool_name: Optional[str] = None
    duration_ms: int = 0

    @classmethod
    def success(cls, data: dict[str, Any] = None, tool_name: str = None) -> "ToolResult":
        """创建成功结果"""
        return cls(success=True, data=data or {}, tool_name=tool_name)

    @classmethod
    def failure(cls, error: str, data: dict[str, Any] = None, tool_name: str = None) -> "ToolResult":
        """创建失败结果"""
        return cls(success=False, error=error, data=data or {}, tool_name=tool_name)

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
        }


class BaseTool:
    """Tool 基类

    所有 Agent Tool 继承此类，提供统一的接口和执行计时。

    用法:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "描述"

            def execute(self, **kwargs) -> ToolResult:
                ...
    """

    name: str = "base_tool"
    description: str = "基础 Tool"

    def execute(self, **kwargs) -> ToolResult:
        """执行 Tool（带计时）

        子类重写 _execute 方法实现具体逻辑。
        """
        start = time.perf_counter()
        try:
            result = self._execute(**kwargs)
            result.tool_name = self.name
            result.duration_ms = int((time.perf_counter() - start) * 1000)
            return result
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return ToolResult.failure(
                error=str(e),
                tool_name=self.name,
                data={"duration_ms": elapsed},
            )

    def _execute(self, **kwargs) -> ToolResult:
        """子类实现具体逻辑"""
        raise NotImplementedError(f"{self.name}: _execute 未实现")

    def __repr__(self) -> str:
        return f"<Tool name={self.name}>"
