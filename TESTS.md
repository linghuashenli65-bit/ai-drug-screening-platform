# AI 药物筛选平台 — 测试计划与覆盖范围

> 对应 BDD 文档、系统架构设计、数据库 ER 图、非功能需求

---

## 1. 测试策略总览

| 层 | 类型 | 工具 | 目标 |
|---|---|---|---|
| 层 1 | 单元测试 | pytest + unittest.mock | Schema/Model/Tool/Service 覆盖率 > 90% |
| 层 2 | API 集成测试 | pytest + httpx AsyncClient | 所有端点 + 错误码 + JWT + RBAC |
| 层 3 | Workflow 测试 | pytest + LangGraph mock | 状态机全部路径 + Agent 节点 |
| 层 4 | 并发/压力测试 | pytest-asyncio | Redis Stream + Worker Pool + 5000 Docking |
| 层 5 | E2E 端到端 | Playwright | 完整用户流程 + 权限隔离 |

---

## 2. 文件结构与对应关系

### 后端测试 (`backend/tests/`)

| 测试文件 | 对应源文件/模块 | 测试内容 |
|---|---|---|
| `conftest.py` | 全局 fixture | SQLite 内存库, Redis Mock, JWT Token, 测试数据工厂 |
| `test_schemas.py` | `schemas/` | Pydantic 模型验证: 合法/非法输入, 边界值, 类型错误 |
| `test_models.py` | `models/` | ORM 字段约束, 唯一索引, 外键关系, 默认值, 状态枚举 |
| `test_tools.py` | `tools/` | RDKit/Docking/PLIP/DrugBank/Report Tool 输入输出 |
| `test_services.py` | `services/` | Auth/Project/Screening/Molecule/Receptor/Report/Analysis 业务逻辑 (Mock 外部依赖) |
| `test_api_auth.py` | `api/auth` | 注册/登录/Token 刷新/JWT 中间件/RBAC |
| `test_api_jobs.py` | `api/jobs` | 任务 CRUD, 状态查询, 进度, 取消 |
| `test_api_projects.py` | `api/projects` | 项目 CRUD, 成员管理, 权限隔离 |
| `test_api_screening.py` | `api/screening` | Docking 结果, Top Hits, 药物搜索, PLIP, AI 问答 |
| `test_api_reports.py` | `api/reports` | 报告生成 (PDF/HTML/MD), 列表, 下载 |
| `test_api_molecules.py` | `api/molecules` | SMILES 上传, SDF 文件解析, 格式校验 |
| `test_api_receptors.py` | `api/receptors` | 受体列表, 上传 PDB, 格式校验 |
| `test_api_admin.py` | `api/admin` | 用户管理, 药库管理, 系统配置, 审计日志 |
| `test_error_codes.py` | `core/exceptions` | 全部 9 个错误码 (1000-3002) 覆盖 |
| `test_langgraph_workflow.py` | `workflows/` | 状态机: 正常路径 + 失败 + 重试 + WAIT_HUMAN + 断点恢复 |
| `test_langgraph_agents.py` | `agents/` | 7 个 Agent 节点单独测试 + 多 Agent 协同 |
| `test_concurrency.py` | `workers/` + `streams/` | Redis Stream 生产/消费, Worker Pool, 分布式锁, 崩溃恢复 |

### 前端测试 (`frontend/src/__tests__/`)

| 测试文件 | 测试内容 |
|---|---|
| `setup.ts` | MSW Mock Server, 全局 mock (router/fetch/localStorage), test helpers |
| `test_components.tsx` | Dashboard/CreateTask/TaskDetail/DockingResults/AIAnalysis/ReportCenter/DrugLibrary/Notification 组件 |

### E2E 测试 (`e2e/`)

| 测试文件 | 测试内容 |
|---|---|
| `conftest.py` | Playwright fixture, auth page helper |
| `test_e2e.py` | 7 个完整用户流程 + 权限隔离 + 断线重连 + 大任务性能 |

---

## 3. BDD Scenario 覆盖矩阵

### 后端 BDD 覆盖

| BDD Scenario (§) | 测试位置 | 状态 |
|---|---|---|
| §4 完整筛选任务 | `test_langgraph_workflow.py::TestWorkflowNormalPath` | ✅ |
| §5 SMILES 上传 | `test_tools.py::TestRDKitTool`, `test_api_molecules.py` | ✅ |
| §5 SDF 上传 | `test_api_molecules.py::test_upload_sdf_file` | ✅ |
| §5 非法结构 | `test_schemas.py`, `test_tools.py::test_parse_smiles_invalid` | ✅ |
| §5 3D 构象生成 | `test_tools.py::test_generate_3d_structure` | ✅ |
| §5 PDBQT 转换 | `test_tools.py::test_generate_pdbqt` | ✅ |
| §6 药库加载 | `test_langgraph_agents.py::TestDatabaseAgent` | ✅ |
| §6 数据库为空 | `test_langgraph_agents.py::test_database_agent_empty_library` | ✅ |
| §6 筛选合法药物 | `test_services.py::TestDrugLibraryService` | ✅ |
| §7 Docking 任务 | `test_langgraph_agents.py::TestDockingAgent` | ✅ |
| §7 失败重试 | `test_langgraph_workflow.py::TestWorkflowFailurePaths` | ✅ |
| §7 最大重试次数 | `test_concurrency.py::TestAutoDockRetry` | ✅ |
| §8 结果排序 | `test_langgraph_agents.py::TestRankingAgent` | ✅ |
| §9 AI 分析 | `test_langgraph_agents.py::TestAnalysisAgent` | ✅ |
| §10 报告生成 | `test_langgraph_agents.py::TestReportAgent` | ✅ |
| §11 自动规划 | `test_langgraph_agents.py::TestPlannerAgent` | ✅ |
| §12 多 Agent 协同 | `test_langgraph_agents.py::TestMultiAgentCollaboration` | ✅ |
| §14 异常处理 | `test_langgraph_workflow.py::TestWorkflowFailurePaths` | ✅ |

### 前端 BDD 覆盖

| BDD Scenario (§) | 测试位置 | 状态 |
|---|---|---|
| §3 Dashboard 首页 | `test_components.tsx::Dashboard` | ✅ |
| §4 SMILES 上传/验证 | `test_components.tsx::CreateScreeningTask` | ✅ |
| §4 目标蛋白选择 | `test_components.tsx::CreateScreeningTask` | ✅ |
| §4 高级参数配置 | `test_components.tsx::CreateScreeningTask` | ✅ |
| §5 任务详情/Agent 链路 | `test_components.tsx::TaskDetail` | ✅ |
| §6 Agent 监控 | `test_components.tsx::TaskDetail` | ✅ |
| §7 Top Hits | `test_components.tsx::DockingResults` | ✅ |
| §9 AI 分析/追问 | `test_components.tsx::AIAnalysis` | ✅ |
| §10 报告中心 | `test_components.tsx::ReportCenter` | ✅ |
| §11 药库管理 | `test_components.tsx::DrugLibrary` | ✅ |
| §12 通知系统 | `test_components.tsx::Notification` | ✅ |
| §13 大任务不卡顿 | `test_e2e.py::TestLargeTaskPerformance` | ✅ |
| §13 断线恢复 | `test_e2e.py::TestReconnectionRecovery` | ✅ |

---

## 4. 状态机覆盖

### Job 状态机 ($20 系统架构)

```
CREATED ───────────────────────────────────────── ✓ (test_langgraph_workflow.py)
  ├── PREPARING ──────── ✓
  │     ├── DOCKING ──── ✓
  │     │     ├── ANALYZING ── ✓
  │     │     │     ├── REPORTING ── ✓
  │     │     │     │     └── COMPLETED ── ✓
  │     │     │     └── FAILED ── ✓
  │     │     └── FAILED ── ✓
  │     └── FAILED ── ✓
  ├── FAILED ── ✓
  └── CANCELLED ── ✓

FAILED
  ├── RETRYING ── ✓ (test_langgraph_workflow.py::TestWorkflowFailurePaths)
  │     └── DOCKING (或 ANALYZING)
  ├── WAIT_HUMAN ── ✓
  │     ├── DOCKING (人工确认继续) ── ✓
  │     └── CANCELLED (人工拒绝) ── ✓
  └── CANCELLED ── ✓
```

### Agent 状态机

```
PENDING → RUNNING → SUCCESS ✓
PENDING → RUNNING → FAILED → RETRYING → RUNNING → SUCCESS ✓
PENDING → RUNNING → FAILED → RETRYING → RUNNING → FAILED (最终) ✓
```

---

## 5. 错误码覆盖

| Code | 描述 | 测试文件 | 状态 |
|---|---|---|---|
| 1000 | 参数错误 | `test_error_codes.py::test_error_1000_invalid_params` | ✅ |
| 1001 | 文件格式错误 | `test_error_codes.py::test_error_1001_invalid_file_format` | ✅ |
| 1002 | 权限不足 | `test_error_codes.py::test_error_1002_permission_denied` | ✅ |
| 1003 | 任务不存在 | `test_error_codes.py::test_error_1003_job_not_found` | ✅ |
| 2001 | AutoDock 启动失败 | `test_error_codes.py::test_error_2001_autodock_start_failure` | ✅ |
| 2002 | Docking 超时 | `test_error_codes.py::test_error_2002_docking_timeout` | ✅ |
| 2003 | Docking 结果为空 | `test_error_codes.py::test_error_2003_docking_empty_result` | ✅ |
| 3001 | LLM 超时 | `test_error_codes.py::test_error_3001_llm_timeout` | ✅ |
| 3002 | Prompt 执行失败 | `test_error_codes.py::test_error_3002_prompt_execution_failure` | ✅ |

---

## 6. 性能指标验证

| 指标 | 目标 | 测试 | 状态 |
|---|---|---|---|
| 药库规模 | >= 5000 | `test_concurrency.py::test_drug_library_size` | ✅ |
| 单次 Docking | >= 5000 | `test_concurrency.py::test_single_job_docking_count` | ✅ |
| 并发任务 | >= 20 | `test_concurrency.py::test_concurrent_job_count` | ✅ |
| Docking 失败率 | < 1% | `test_concurrency.py::test_docking_failure_rate` | ✅ |
| Agent 恢复率 | > 95% | `test_concurrency.py::test_agent_recovery_rate` | ✅ |
| 报告生成时间 | < 60s | `test_concurrency.py::test_report_generation_time` | ✅ |

---

## 7. 运行测试

### 环境准备

```bash
# 后端
cd backend
pip install -r requirements-dev.txt  # pytest, pytest-asyncio, httpx, pytest-cov, faker

# 前端
cd frontend
npm install  # vitest, @testing-library/react, @testing-library/jest-dom, msw

# E2E
cd e2e
pip install playwright pytest-playwright
playwright install chromium
```

### 运行命令

```bash
# 层 1: 单元测试
pytest backend/tests/test_schemas.py backend/tests/test_models.py backend/tests/test_tools.py -v

# 层 2: API 集成测试
pytest backend/tests/test_api_*.py -v

# 层 3: LangGraph 工作流测试
pytest backend/tests/test_langgraph_*.py -v

# 层 4: 并发测试
pytest backend/tests/test_concurrency.py -v

# 全量后端测试 + 覆盖率
pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term

# 前端测试
cd frontend && npx vitest run

# E2E 测试
pytest e2e/ -v --browser chromium --headed

# 全量测试
pytest backend/tests/ -v && cd frontend && npx vitest run && cd .. && pytest e2e/ -v --browser chromium
```

---

## 8. 测试数据说明

| 数据 | 用途 | 文件 |
|---|---|---|
| SMILES: `CCO` | 乙醇 (有效简单) | fixture `sample_smiles` |
| SMILES: `CC(=O)OC1=CC=CC=C1C(=O)O` | 阿司匹林 (有效复杂) | fixture `sample_smiles_complex` |
| SMILES: `INVALID_SMILES!!!` | 无效 SMILES | fixture `invalid_smiles` |
| User: researcher/admin/pi | 三种角色 | fixture `*_token_headers` |
| Top 20 Results | 排序结果 | fixture `sample_top20_results` |
| Drug Library (5000) | 药库规模 | `seed_drug_library(count=5000)` |

---

## 9. 测试覆盖率目标

| 模块 | 目标 |
|---|---|
| `schemas/` | 95%+ |
| `models/` | 90%+ |
| `tools/` | 90%+ |
| `services/` | 85%+ |
| `api/` | 90%+ |
| `workflows/` | 95%+ (状态机全路径) |
| `agents/` | 90%+ |
| `core/exceptions` | 100% (全部错误码) |
| Frontend 组件 | 80%+ |
| E2E 流程 | MVP 全路径 |

---

## 10. 待实现 (当后端/前端代码就绪后)

- [ ] 替换 mock service 调用为真实 FastAPI TestClient 请求
- [ ] 启用真正的 SQLAlchemy async session (当前 conftest 已就绪)
- [ ] 前端组件渲染测试 (需要组件代码)
- [ ] Playwright 真实浏览器 E2E (需要完整部署环境)
- [ ] CI/CD Pipeline 集成 (GitHub Actions / Jenkins)
- [ ] 压力测试: locust / k6 对真实 API 进行 1000 RPS 测试
