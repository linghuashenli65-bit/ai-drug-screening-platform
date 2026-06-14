# AI Drug Screening Platform - Backend

AI 药物虚拟筛选平台后端服务，基于 FastAPI + LangGraph 构建。

## 技术栈

- **框架**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2 (async)
- **Agent 编排**: LangGraph (状态机工作流)
- **LLM**: DeepSeek API (OpenAI 兼容, requests 直连)
- **消息队列**: Redis Stream
- **向量检索**: Milvus 2
- **对接引擎**: AutoDock Vina + RDKit + Meeko
- **对象存储**: MinIO (S3 兼容)

## 项目结构

```
app/
├── main.py                 # FastAPI 应用入口
├── api/                    # API 路由层
│   ├── auth.py             # 认证 (JWT)
│   ├── screening.py        # 筛选任务 CRUD + 工作流触发
│   ├── drugs.py            # 药物库管理
│   └── reports.py          # 报告管理
├── agents/                 # LangGraph Agent 节点
│   ├── graph.py            # 工作流图定义
│   ├── planner_agent.py    # 任务规划
│   ├── molecule_agent.py   # 分子预处理
│   ├── database_agent.py   # 数据库查询
│   ├── docking_agent.py    # 对接任务分发
│   ├── ranking_agent.py    # 结果排序
│   ├── analysis_agent.py   # AI 分析
│   └── report_agent.py     # 报告生成
├── core/                   # 核心模块
│   ├── config.py           # Pydantic Settings 配置
│   ├── database.py         # 数据库连接池
│   ├── security.py         # JWT + 密码加密 + Prompt 注入检测
│   ├── logger.py           # structlog 日志
│   ├── redis.py            # Redis 连接
│   ├── milvus.py           # Milvus 连接
│   └── exceptions.py       # 统一异常体系
├── models/                 # SQLAlchemy 模型
│   ├── user.py             # 用户模型
│   ├── screening.py        # 筛选任务 + 对接结果
│   ├── drug.py             # 药物模型
│   └── report.py           # 报告模型
├── tools/                  # Agent 可调用工具
│   ├── base.py             # BaseTool + ToolResult
│   ├── llm/client.py       # LLM 客户端 (requests 直连)
│   ├── docking/            # 分子对接工具
│   └── database/           # 数据库查询工具
└── workers/                # 后台服务
    ├── scheduler.py        # 任务调度器 (进度同步/超时重试)
    └── docking_worker.py   # 对接计算 Worker (Redis 消费者)
```

## Agent 工作流

```
START → planner → molecule → database → docking → ranking → analysis → report → END
```

每个节点是一个 LangGraph Agent，通过共享 State 传递数据。

## 运行方式

### Docker (推荐)

```bash
# 在项目根目录
docker compose up -d backend scheduler docking-worker
```

### 本地开发

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

需要本地配置 MySQL、Redis、Milvus、MinIO。

## 配置

通过环境变量或 `.env` 文件配置，主要参数：

| 变量 | 说明 |
|------|------|
| `MYSQL_HOST` / `MYSQL_PORT` | MySQL 连接 |
| `REDIS_HOST` / `REDIS_PORT` | Redis 连接 |
| `MILVUS_HOST` / `MILVUS_PORT` | Milvus 连接 |
| `MINIO_ENDPOINT` | MinIO 地址 |
| `OPENAI_API_KEY` | LLM API 密钥 |
| `OPENAI_BASE_URL` | LLM API 基础地址 |
| `OPENAI_MODEL` | 使用的模型 |
| `SECRET_KEY` | JWT 签名密钥 |
| `DOCKING_SIMULATION_MODE` | 模拟对接模式 (无 Vina 时) |

## 测试

```bash
pytest tests/ -v
```

## API 文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
