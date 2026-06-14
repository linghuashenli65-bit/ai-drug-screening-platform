# AI Drug Screening Platform

AI 驱动的高通量药物虚拟筛选平台，集成分子对接、智能分析和自动化报告生成。

## 系统架构

```
┌─────────────┐     ┌─────────────────────────────────────────┐
│   Frontend  │────▶│              Backend API                 │
│  React+Vite │     │           FastAPI + Uvicorn              │
└─────────────┘     └────────┬──────────┬──────────┬──────────┘
                             │          │          │
                    ┌────────▼───┐ ┌────▼────┐ ┌──▼───────────┐
                    │   MySQL    │ │  Redis  │ │    Milvus    │
                    │  任务/结果  │ │ 消息队列 │ │  向量数据库   │
                    └────────────┘ └─────────┘ └──────────────┘
                             │          │
                    ┌────────▼───┐ ┌────▼────────────┐
                    │   MinIO    │ │  Docking Worker  │
                    │  文件存储   │ │  分子对接计算     │
                    └────────────┘ └─────────────────┘
```

### 核心流程

1. **任务创建** → 用户提交靶点蛋白 + 药物库
2. **LangGraph Agent 编排** → Planner → Molecule → Database → Docking → Ranking → Analysis → Report
3. **分子对接** → Redis Stream 分发任务，Worker 并行计算
4. **AI 分析** → LLM 生成候选药物分析、重定位建议、风险评估
5. **报告输出** → 自动生成筛选报告

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Ant Design 5, Vite, Zustand |
| 后端 | Python 3.12, FastAPI, SQLAlchemy 2, LangGraph |
| 数据库 | MySQL 8, Redis 7, Milvus 2 |
| 对接引擎 | AutoDock Vina, RDKit, Meeko |
| AI/LLM | DeepSeek API (OpenAI 兼容) |
| 存储 | MinIO (S3 兼容) |
| 部署 | Docker Compose |

## 快速开始

### 前置条件

- Docker Desktop (>= 4.0)
- Docker Compose V2

### 1. 克隆项目

```bash
git clone <repo-url>
cd ai-drug-screening-platform
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key
```

### 3. 启动所有服务

```bash
docker compose up -d
```

等待所有服务健康检查通过（约 30-60 秒），然后访问：

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| 后端 API | http://localhost:18000/api/v1 |
| MinIO 控制台 | http://localhost:9001 |
| API 文档 | http://localhost:18000/docs |

### 4. 创建账号

首次使用需注册账号，访问 http://localhost:3000/register

## 项目结构

```
ai-drug-screening-platform/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── agents/            # LangGraph Agent 节点
│   │   ├── core/              # 配置、安全、日志
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── tools/             # Agent 工具集
│   │   │   ├── llm/           # LLM 客户端
│   │   │   ├── docking/       # 分子对接工具
│   │   │   └── database/      # 数据库查询工具
│   │   └── workers/           # 后台任务 Worker
│   │       ├── scheduler.py   # 任务调度器
│   │       └── docking_worker.py  # 对接计算 Worker
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # 公共组件
│   │   ├── services/          # API 调用
│   │   ├── stores/            # 状态管理
│   │   └── types/             # TypeScript 类型
│   ├── package.json
│   └── Dockerfile
├── e2e/                        # 端到端测试
├── docker-compose.yml          # 服务编排
├── .env.example                # 环境变量模板
└── README.md
```

## 主要功能

### 药物筛选
- 支持 SMILES、SDF 格式输入
- 内置多个药物库（FDA 批准药物、天然产物等）
- 自动分子预处理和 3D 构象生成

### 分子对接
- AutoDock Vina 引擎
- Redis Stream 并行任务分发
- 实时进度推送 (SSE)
- 模拟模式（无 Vina 环境可用时）

### AI 智能分析
- 候选药物深度分析
- 药物重定位建议
- 风险评估和安全性提示
- 实验方案建议
- 交互式 AI 追问对话

### 可视化
- 3D 蛋白-配体结合结构 (3Dmol.js)
- 对接结果排行榜
- 对接得分分布图

### 报告
- 自动生成筛选报告
- PDF 导出

## Docker 服务说明

| 服务 | 容器名 | 端口 | 用途 |
|------|--------|------|------|
| frontend | drug-screening-frontend | 3000 | Nginx 托管前端 SPA |
| backend | drug-screening-backend | 18000 | FastAPI 主服务 |
| scheduler | drug-screening-scheduler | - | 任务调度和进度同步 |
| docking-worker | drug-screening-docking-worker | - | 分子对接计算 |
| mysql | drug-screening-mysql | 3306 | 主数据库 |
| redis | drug-screening-redis | 6379 | 消息队列 + 缓存 |
| milvus | drug-screening-milvus | 19530 | 分子向量检索 |
| minio | drug-screening-minio | 9000/9001 | 文件对象存储 |

## 常用命令

```bash
# 查看所有服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 重建单个服务
docker compose build backend && docker compose up -d backend

# 停止所有服务
docker compose down

# 停止并清除数据卷
docker compose down -v
```

## API 概览

后端 API 遵循 RESTful 设计，完整文档见 http://localhost:18000/docs

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /auth/login` | JWT 登录 |
| 认证 | `POST /auth/register` | 用户注册 |
| 筛选 | `POST /screenings` | 创建筛选任务 |
| 筛选 | `GET /screenings` | 任务列表 |
| 筛选 | `GET /screenings/{id}` | 任务详情 |
| 筛选 | `GET /screenings/{id}/events` | SSE 实时进度 |
| 结果 | `GET /screenings/{id}/results` | 对接结果 |
| 分析 | `GET /screenings/{id}/analysis` | AI 分析报告 |
| 分析 | `POST /screenings/{id}/analysis/chat` | AI 追问 |
| 药物库 | `GET /drugs` | 药物查询 |
| 药物库 | `POST /drugs/import` | CSV 导入 |
| 报告 | `GET /reports` | 报告列表 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | LLM API 密钥（必填） |
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
| `OPENAI_MODEL` | `deepseek-chat` | 主模型 |
| `LLM_FALLBACK_MODEL` | `deepseek-chat` | 备用模型 |
| `MYSQL_ROOT_PASSWORD` | `root` | MySQL 密码 |
| `SECRET_KEY` | - | JWT 签名密钥 |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO 访问密钥 |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO 密钥 |

## 开发说明

### 后端开发

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

详见 [frontend/README.md](./frontend/README.md)

## License

MIT
