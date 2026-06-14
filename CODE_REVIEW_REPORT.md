# 代码审核报告

**审核日期**: 2026-06-13 (第三轮)  
**审核人**: 代码审核 Agent  
**审核范围**: `ai-drug-screening-platform/` 全部已提交代码 (60+ 文件, ~6000+ 行)  
**设计文档基准**: 目录结构设计.md / 数据库设计.md / 数据库ER.md / 系统架构设计.md / 非功能需求.md

---

## 一、总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构一致性 | 4/5 | DDD 六层目录完整 (API/Service/Workflow/Agent/Tool/Infrastructure)，Agent->Tool 组合模式正确实现；API/Service/Worker 三层尚未实现 |
| 数据边界 | 5/5 | 14 个 ORM 模型通过全部 5 条反模式检查；URI 存储而非 BLOB；Redis/Milvus 职责边界明确 |
| 安全性 | 3/5 | JWT+RABC 基础扎实；sanitize_prompt 分层违规/SSE Token URL 传递/前端 CDN 无 SRI 三项需修复 |
| 代码质量 | 4/5 | Agent->Tool 模式实现优雅，PDBQT 三级回退设计良好；少数 async/sync 不一致、未使用导入需清理 |
| 测试覆盖 | 3/5 | 测试文件覆盖全部层次 (12 个 test_*.py)，但多数测试使用 mock 而非真实被测代码导入，无法验证接口一致性 |

**总体结论**: Phase 2-4 (models/schemas/tools/agents) 全部完成，质量良好。Phase 5 (workflows) 仅有 __init__.py 骨架。Phase 6-8 (API/Service/Worker) 尚未开始。**前端 9 个页面全部完成，App.tsx 已集成 React Router（上一轮阻塞项已解除）。** 测试文件框架完整但大多运行 mock 逻辑，需与实际代码对接。

---

## 二、架构一致性审查

### 2.1 DDD 分层完成度

| 层 | 状态 | 文件数 | 说明 |
|----|------|--------|------|
| API (`api/`) | 未实现 | 0 | 目录为空 |
| Service (`services/`) | 未实现 | 0 | 目录为空 |
| Workflow (`workflows/`) | 骨架 | 1 | 仅 `__init__.py` 文档字符串，states.py/nodes.py/routes.py/graph_builder.py 均未创建 |
| Agent (`agents/`) | 完成 | 7 | Planner/Molecule/Database/Docking/Ranking/Analysis/Report |
| Tool (`tools/`) | 完成 | 20+ | 7 个包: rdkit/autodock/llm/plip/pubmed/drugbank/report |
| Infrastructure (`core/`) | 完成 | 10 | config/database/exceptions/security/redis/milvus/minio/logger/constants |

### 2.2 Agent->Tool 模式验证

所有 Agent 均通过组合模式持有 Tool 实例，不直接操作外部系统:
- MoleculeAgent: RdkitParser + RdkitDescriptors + RdkitConformer + RdkitPdbqtConverter
- DockingAgent: AutoDockTaskBuilder
- RankingAgent: AutoDockScoreExtractor
- AnalysisAgent: LLMChain + LLMClient
- ReportAgent: ReportGenerator
- DatabaseAgent: DrugbankQuery (声明但未在 _execute 中使用)

Tool 均通过 `ToolResult.success()/.failure()` 返回结果，Agent 通过 `AgentRunResult.success()/.failed()` 返回。两层返回值模式一致。

---

## 三、数据边界检查

### 3.1 五条反模式逐项验证

| # | 反模式 | 验证结果 | 证据 |
|---|--------|---------|------|
| 1 | BLOB 存储分子文件 | **通过** | 所有模型使用 VARCHAR URI 字段(pdbqt_uri, sdf_uri, report_uri)，二进制文件存 MinIO |
| 2 | Redis 作为状态唯一真相源 | **通过** | redis.py 文档注释明确"以 MySQL 为准"，Streams+Hash 仅运行态缓存 |
| 3 | Docking 结果存入 Milvus | **通过** | milvus.py 仅存 Morgan 2048-bit 指纹，Docking 分数存 MySQL docking_tasks 表 |
| 4 | 每个 Docking 任务独立 Redis Key | **通过** | redis.py 使用 Stream 批量消费 + Hash 聚合进度(TTL 24h)，无逐任务独立 Key |
| 5 | Milvus 用于精确过滤 | **通过** | milvus.py 仅提供 `search_similar_drugs()` 相似性检索，精确过滤走 MySQL |

### 3.2 ORM 模型数据边界

- `analysis.py:32`: `analysis_json: Mapped[dict] = mapped_column(JSON)` — 使用 `mysql.JSON`，与 SQLite 测试环境不兼容
- `screening.py:34`: `created_by: Mapped[int]` 缺少 `ForeignKey("users.id")`，上一轮已报告，仍未修复
- 其余 12 个模型全部通过: user/project/molecule/docking/receptor/report/agent/audit

---

## 四、安全性审查

### 4.1 已修复项（较上一轮）

无。上一轮所有安全问题仍然存在。

### 4.2 持续存在的问题

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | **严重** | `security.py:246` | `sanitize_prompt()` 抛出 `HTTPException`（core 层依赖 web 框架） | 抛出 `PromptInjectionError`，由全局异常处理器转换为 HTTP 400 |
| 2 | **严重** | `useSSE.ts:29` | JWT Token 通过 URL query 参数传递，出现在服务器日志/浏览器历史中 | 使用 fetch + ReadableStream 实现 SSE（支持自定义 header） |
| 3 | **严重** | `milvus.py:174` | `f'drug_id == {drug_id}'` f-string 表达式注入 | 添加 `assert isinstance(drug_id, int)` 类型断言 |
| 4 | 中等 | `config.py:28` | `SECRET_KEY` 有默认有效值，生产环境未覆写时 JWT 可伪造 | 改为空字符串，startup 时检查非 DEBUG 下必须设置 |
| 5 | 中等 | `api.ts:33` | Access Token 存 localStorage（XSS 窃取风险） | 生产环境使用 httpOnly Cookie |
| 6 | 中等 | `authService.ts:6-9` | login 使用 FormData 传递 OAuth2 密码，后端期望 URL-encoded | 改用 `URLSearchParams` |

### 4.3 本轮新发现的安全问题

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 7 | 中等 | `StructureViewPage.tsx:71-77` | 动态注入 `<script>` 标签加载 3Dmol.js CDN，无 SRI hash，无 CSP 头 | 使用 npm 包 `3dmol` 替代 CDN，或添加 `integrity` 属性 |
| 8 | 建议 | `config.py:140-148` | Prompt Injection 模式仅 6 个固定字符串，单字符变换即可绕过 | 在 `sanitize_prompt()` 中先做 Unicode NFKC 规范化再匹配 |
| 9 | 建议 | `llm/client.py:73-75` | 仅检查 `role == "user"` 的消息，system 消息未做注入检测 | 对所有消息 content 执行 sanitize，或至少对 user+system 角色检测 |

---

## 五、状态机验证

### 5.1 后端实现

`constants.py` 定义 `VALID_JOB_TRANSITIONS` 和 `can_transition()` 函数，完整实现:

```
CREATED → PREPARING → DOCKING → ANALYZING → REPORTING → COMPLETED
                ↓          ↓           ↓            ↓
              FAILED     FAILED      FAILED       FAILED
                ↓          ↓           ↓            ↓
             RETRYING   RETRYING    RETRYING     RETRYING
```

PlannerAgent (`planner_agent.py:48-71`) 覆盖所有状态分支: CREATED/PREPARING/DOCKING/ANALYZING/REPORTING/FAILED/RETRYING/WAIT_HUMAN。

### 5.2 前端实现

前端 `JobStatus` 类型与后端枚举完全一致 (9 个状态值相同)。Dashboard/TaskList/TaskDetail 三页面均正确使用 statusColorMap/statusLabelMap。

### 5.3 缺失项

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | 中等 | `workflows/` | `can_transition()` 虽已定义，但无 workflow 代码调用它；PlannerAgent 自行判断状态，未使用 `can_transition()` 校验 | 在 workflow graph builder 中，每个状态变更前调用 `can_transition()` |

---

## 六、错误码检查

`exceptions.py` 完整覆盖 6 个错误码系列:
- 1000 系列: General/Validation (1000-1007)
- 2000 系列: Docking (2000-2005)
- 3000 系列: AI Analysis (3000-3004)
- 4000 系列: Agent (4000-4003)
- 5000 系列: Workflow (5000-5004)
- 6000 系列: Storage (6000-6003)

`constants.py` `ERROR_CODES` 字典汇总所有错误码。

遗留问题: `PromptInjectionError`(行160-163) 继承 `AIAnalysisError`(3002)，语义应为 ValidationError(1000 系列)。

---

## 七、分层代码审查

### 7.1 Models 层 (Phase 2) — 评分: 4.5/5

**良好**: 14 个 ORM 模型均使用 SQLAlchemy 2.0 Mapped 类型，关系映射正确，`__tablename__` 显式声明，索引合理。

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | 中等 | `analysis.py:32` | `analysis_json: Mapped[dict]` 使用 `mysql.JSON`，SQLite 测试无法创建表 | 使用 `sqlalchemy.JSON` 或条件导入 |
| 2 | 中等 | `screening.py:34` | `created_by` 缺少 `ForeignKey("users.id")` | 添加 ForeignKey 约束 |
| 3 | 建议 | `molecule.py` | DrugLibrary 模型 `molecular_weight`/`logp` 等可为 NULL，但计算描述符时已赋值 | 确认业务是否允许 NULL |

### 7.2 Schemas 层 (Phase 2) — 评分: 4/5

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | 中等 | `screening.py:29-32` | `ScreeningCreateRequest` 缺少 `exhaustiveness`/`num_cpus`/`top_n` 字段，而前端 CreateTaskPage 发送这些字段 | 添加字段: `exhaustiveness: int = 8`, `cpu_count: int = 4`, `top_n: int = 20` |
| 2 | 建议 | `common.py` | `ProjectResponse` 放在 common.py 而非 project schema | 移至独立 `schemas/project.py` |
| 3 | 建议 | `auth.py` | `RegisterRequest.email` 使用 `str` 而非 `EmailStr` | 使用 `pydantic.EmailStr` 校验 |

### 7.3 Tools 层 (Phase 3) — 评分: 4.5/5

**良好**: 7 个工具包实现完整，Agent->Tool 组合模式正确，PDBQT 转换三级回退(Meeko→obabel→RDKit)设计优秀。

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | 中等 | `minio.py:72-97` | `upload_file`/`upload_bytes`/`download_file` 标记 `async` 但内部同步调用 minio-py | 使用 `asyncio.to_thread()` 包装同步调用 |
| 2 | 中等 | `milvus.py:121-133` | `insert_drug_vector`/`search_similar_drugs` 同理标记 async 但同步执行 | 同上 |
| 3 | 建议 | `llm/chains.py:49` | Prompt 模板使用 `str.format()`，若字段含 `{}` 会抛 KeyError | 使用 `str.replace()` 或 Jinja2 模板 |
| 4 | 建议 | `pubmed/search.py:109` | `time.sleep(0.34)` 在 async 函数中阻塞事件循环 | 使用 `asyncio.sleep(0.34)` |
| 5 | 建议 | `report/generator.py:219` | `import markdown` 放在 `generate_html` 方法内部（延迟导入），每次调用都重复 import | 移至文件顶部 |

### 7.4 Agents 层 (Phase 4) — 评分: 4.5/5

**良好**: 7 个 Agent 覆盖完整虚拟筛选链路，`_validate_input` / `_execute` / `_format_output` 三方法模式一致，状态分支处理完整。

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | 中等 | `docking_agent.py:21` | `from app.core.redis import stream_add, get_redis` — `get_redis` 导入但未使用 | 删除未使用导入 |
| 2 | 中等 | `database_agent.py:22` | 导入 `DrugbankQuery` 并在 `__init__` 实例化但 `_execute` 中从未使用 | 若后续使用则保留，否则移除 |
| 3 | 中等 | `report_agent.py:90` | `await upload_file(...)` 调用非 async 函数 | 见 minio.py async 问题 |
| 4 | 建议 | `agent/base.py:72` | `import time` 在 `arun()` 方法内部，每次调用重复导入 | 移至文件顶部 |
| 5 | 建议 | `docking_agent.py:76-100` | `_enqueue_tasks` 逐个 `await stream_add`，5000 任务需 5000 次网络往返 | 考虑使用 Redis Pipeline 批量写入 |

### 7.5 Workflows 层 (Phase 5) — 评分: 1/5

**仅有骨架**。`workflows/__init__.py` 声明了 states.py/nodes.py/routes.py/graph_builder.py 的规划，但均未创建。Phase 5 实际上未开始实施。

### 7.6 前端 (Phases 14-17) — 评分: 4/5

**重大进展**: App.tsx 已完整集成 React Router 和全部 9 个页面（上一轮阻塞项已解除）。

所有页面完整实现:
- DashboardPage: 统计卡片 + 最近任务表
- TaskListPage: 分页/筛选/搜索
- CreateTaskPage: SMILES 校验 + SDF 上传 + 高级参数
- TaskDetailPage: SSE 实时更新 + Agent 执行链路可视化 + 节点日志弹窗
- DockingResultsPage: 结果表/搜索/排序/药物详情弹窗
- AIAnalysisPage: AI 分析折叠面板 + 追问聊天
- ReportCenterPage: 报告列表/预览/下载(PDF/MD)
- DrugLibraryPage: 药物库统计/搜索/CSV 导入
- AgentMonitorPage: 10s 轮询 + Agent 统计 + 节点记录表
- StructureViewPage: 3Dmol.js 3D 结构渲染 + 相互作用可视化

| # | 严重度 | 位置 | 问题 | 修复建议 |
|---|--------|------|------|---------|
| 1 | **严重** | `types/index.ts:4` | `UserRole = 'researcher' \| 'pi' \| 'admin'` (小写，缺 VIEWER) 与后端 `ADMIN\|PI\|RESEARCHER\|VIEWER` 不匹配 | 改为 `'ADMIN' \| 'PI' \| 'RESEARCHER' \| 'VIEWER'` |
| 2 | **严重** | `AppLayout.tsx:112-115` | `roleLabel` 使用小写 key (`admin/pi/researcher`) 与后端枚举大小写不一致 | 统一为大写 |
| 3 | **严重** | `AppLayout.tsx:56-57` | `ProtectedRoute roles={['pi', 'admin']}` 使用小写，`hasRole` 函数将直接比较后端大写值 | 统一为大写 |
| 4 | 中等 | `CreateTaskPage.tsx:32-41` | `mockProteins` 硬编码 8 个蛋白，非生产数据 | 改为从 API 动态获取 `/receptors` |
| 5 | 中等 | `CreateTaskPage.tsx:43` | SMILES 正则 `SMILES_REGEX` 过于宽松（未验证芳香性），`validateSMILES` 仅括号匹配 | 后端已有 RDKit 验证，前端可保留基础检查 |
| 6 | 中等 | `AIAnalysisPage.tsx:94` | 聊天消息直接发送到 `/jobs/${jobId}/analysis/chat`，未经前端注入过滤 | 在后端端点添加 `sanitize_prompt()` 调用 |
| 7 | 建议 | `AppLayout.tsx:59` | 菜单项 '/settings' 路由未在 App.tsx 中注册 | 注册 Settings 路由或移除菜单项 |
| 8 | 建议 | `taskService.ts` | `Content-Type: 'multipart/form-data'` 拼写错误，正确应为 `'multipart/form-data'` | 修正拼写: `multipart/form-data` -> `multipart/form-data` |
| 9 | 建议 | `drugLibService.ts:27` | 同样存在 Content-Type 拼写问题 | 同上 |

---

## 八、测试代码审查

### 8.1 测试文件覆盖

| 测试文件 | 覆盖层次 | 状态 |
|----------|---------|------|
| `test_schemas.py` | Schema 验证 | BDD 风格，使用 mock 导入 |
| `test_models.py` | Model 字段/关系 | 使用 SQLite 内存库 |
| `test_tools.py` | Tool 层 | 使用 mock 路径不匹配实际模块 |
| `test_services.py` | Service 层 | Service 目录为空 |
| `test_langgraph_agents.py` | Agent 层 | 使用 mock 逻辑 |
| `test_langgraph_workflow.py` | Workflow 层 | Workflow 目录为空 |
| `test_api_auth.py` | API 认证 | API 目录为空 |
| `test_api_jobs.py` | API 任务 | API 目录为空 |
| `test_api_molecules.py` | API 分子 | API 目录为空 |
| `test_api_projects.py` | API 项目 | API 目录为空 |
| `test_api_receptors.py` | API 受体 | API 目录为空 |
| `test_api_reports.py` | API 报告 | API 目录为空 |
| `test_api_screening.py` | API 筛选 | API 目录为空 |
| `test_api_admin.py` | API 管理 | API 目录为空 |
| `test_concurrency.py` | 并发/压力 | 使用 MockRedis |

### 8.2 核心问题

| # | 严重度 | 问题 | 影响 |
|---|--------|------|------|
| 1 | **严重** | 所有测试文件使用 mock 路径和模拟逻辑，未导入实际被测模块 | 测试通过不代表代码正确，无法检测接口不匹配 |
| 2 | **严重** | `test_tools.py:78` mock 路径 `backend.tools.rdkit_tool.gen_3d_structure` 与实际路径 `app.tools.rdkit.conformer` 不匹配 | 测试永远找不到模块 |
| 3 | **严重** | 8 个 API 测试文件 (test_api_*.py) 测试的 API 目录为空 | 测试全部会因 ImportError 失败 |
| 4 | 中等 | `conftest.py` Token fixture 仍使用 dict 调用 `create_access_token(data={...})`，但函数签名为 `(user_id, username, role)` | 与上一轮相同，仍未修复 |

---

## 九、阻塞项（必须立即修复）

| # | 位置 | 问题 | 轮次 |
|---|------|------|------|
| 1 | `database.py:58-66` | `get_db()` 事务管理缺陷 (finally close + yield 后 commit) | R1 |
| 2 | `security.py:246` | `sanitize_prompt()` 抛出 HTTPException（分层违规） | R1 |
| 3 | `types/index.ts:4` | UserRole 小写 + 缺 VIEWER，与后端枚举不匹配 | R2 |
| 4 | `AppLayout.tsx:56-57,112-115` | 角色检查全部使用小写，与后端大写不匹配 | R3 |
| 5 | `useSSE.ts:29` | JWT Token 通过 URL query 参数传递 | R2 |
| 6 | `screening.py:34` | `created_by` 缺少 ForeignKey("users.id") | R2 |
| 7 | `analysis.py:32` | `mysql.JSON` 与 SQLite 测试不兼容 | R3 |
| 8 | `conftest.py:227-275` | Token fixture 与 security.py 接口不匹配 (5 处) | R1 |
| 9 | `test_tools.py:78` | mock 路径 `backend.tools.rdkit_tool` 与实际路径 `app.tools.rdkit` 不匹配 | R3 |
| 10 | `minio.py:72-97` / `milvus.py:121-133` | async 函数内部同步操作 | R1 |
| 11 | `milvus.py:174` | delete 表达式 f-string 注入风险 | R1 |
| 12 | `StructureViewPage.tsx:71-77` | CDN 动态脚本注入无 SRI hash | R3 |
| 13 | `screening.py:29-32` | ScreeningCreateRequest 缺少 exhaustiveness/cpu_count/top_n 字段 | R3 |
| 14 | `workflows/` | Phase 5 仅有骨架，states.py/nodes.py/routes.py/graph_builder.py 均未实现 | R3 |

## 十、建议项（非阻塞）

| # | 位置 | 问题 | 轮次 |
|---|------|------|------|
| 1 | `config.py:28` | SECRET_KEY 有默认值 | R1 |
| 2 | `config.py:140-148` | Prompt Injection 模式需 Unicode 规范化 | R1 |
| 3 | `database.py:43` | Base 注释声称自动复数化不实 | R1 |
| 4 | `logger.py:51` | 全局 logger 在 setup 前创建 | R1 |
| 5 | `main.py:95-105` | 请求日志应区分成功/失败级别 | R1 |
| 6 | `main.py:139-146` | 未捕获异常 code=9999 不在规范中 | R1 |
| 7 | `authService.ts:6-9` | login 使用 FormData 而非 URLSearchParams | R2 |
| 8 | `useSSE.ts:66` | SSE 错误处理无重连限制 | R2 |
| 9 | `docking_agent.py:21` | 未使用导入 `get_redis` | R3 |
| 10 | `database_agent.py:22` | 未使用导入 `DrugbankQuery` | R3 |
| 11 | `pubmed/search.py:109` | async 函数内 `time.sleep()` 阻塞事件循环 | R3 |
| 12 | `agent/base.py:72` | `import time` 在方法内部 | R3 |
| 13 | `CreateTaskPage.tsx:32` | mockProteins 硬编码 | R3 |
| 14 | `CreateTaskPage.tsx:43` | SMILES_REGEX 无法验证环闭合(如 c1ccccc1) | R3 |
| 15 | `AppLayout.tsx:59` | /settings 路由未在 App.tsx 注册 | R3 |
| 16 | `taskService.ts` / `drugLibService.ts` | Content-Type `multipart/form-data` 拼写错误 | R3 |
| 17 | `exceptions.py:160-163` | PromptInjectionError 继承 AIAnalysisError 而非 ValidationError | R1 |

---

## 十一、Phase 5 开工前检查清单

workflows/ 实施前必须准备:

1. 创建 `states.py`: 定义 `ScreeningState(TypedDict)`，字段与 Agent 输入输出对齐
2. 创建 `nodes.py`: 7 个 Agent 对应的 LangGraph 节点函数
3. 创建 `routes.py`: 条件路由逻辑（成功→下一步/失败→重试/人工→等待）
4. 创建 `graph_builder.py`: 构建完整 LangGraph StateGraph
5. 每个状态变更前调用 `can_transition()` 校验合法性
6. 断点恢复: 读取 `agent_runs` 表最近成功节点，从断点继续
7. Agent 执行结果写入 `agent_runs` 和 `tool_calls` 审计表

---

## 十二、已完成项（较上一轮）

| 项 | 说明 |
|----|------|
| App.tsx 集成 React Router | 上一轮阻塞项 #1，现已完整实现 9 个页面路由 |
| Models 层 14 个 ORM 模型 | 数据边界全部通过 5 条反模式验证 |
| Schemas 层 5 个模块 | 覆盖 auth/common/screening/molecule/report |
| Tools 层 7 个工具包 | 20+ Tool 实现，Agent->Tool 组合模式正确 |
| Agents 层 7 个 Agent | 覆盖完整虚拟筛选链路 |
| 前端 9 个页面 + 5 个 Service | 完整 UI 层实现 |
| 测试 14 个文件 | 框架完整，需与实际代码对接 |
