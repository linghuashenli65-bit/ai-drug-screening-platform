"""
Worker 层 — 高通量计算任务执行

每个 Worker 独立进程，消费 Redis Stream 消息队列：
- docking_worker: 执行 AutoDock Vina 对接计算
- analysis_worker: 执行 AI 分析任务
- report_worker: 执行报告生成任务
- scheduler: 任务分发、重试、失败恢复
"""
