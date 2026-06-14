"""
Agent 层 — 智能体执行单元

每个 Agent 遵循统一模式：输入验证 → Tool 调用 → 输出标准化
Agent 之间通过 LangGraph State 通信，不直接相互调用。
"""
