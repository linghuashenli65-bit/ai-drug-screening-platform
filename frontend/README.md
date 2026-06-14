# AI Drug Screening Platform - Frontend

AI 驱动的高通量药物虚拟筛选平台前端，基于 React 18 + TypeScript + Ant Design 构建。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Ant Design 5
- **状态管理**: Zustand
- **路由**: React Router v6
- **HTTP**: Axios (JWT 自动刷新)
- **实时通信**: SSE (Server-Sent Events)
- **3D 可视化**: 3Dmol.js

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## 环境变量

在 `.env` 文件中配置：

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 项目结构

```
src/
├── components/          # 公共组件
│   ├── AppLayout.tsx    # 主布局（侧边栏 + 顶栏 + 内容区）
│   ├── ProtectedRoute.tsx  # 路由守卫（JWT + RBAC）
│   ├── LoadingState.tsx # 加载状态组件
│   ├── EmptyState.tsx   # 空状态组件
│   └── ErrorState.tsx   # 错误状态组件
├── pages/               # 页面组件
│   ├── auth/            # 登录 / 注册 / 403
│   ├── dashboard/       # Dashboard 首页
│   ├── tasks/           # 任务创建 / 任务列表 / 任务详情
│   ├── monitor/         # Agent 执行监控
│   ├── results/         # Docking 结果 / 结构可视化 / AI 分析
│   ├── reports/         # 报告中心
│   └── druglib/         # 药物库管理
├── services/            # API 调用封装
│   ├── api.ts           # Axios 实例 + JWT 拦截器
│   ├── authService.ts   # 认证服务
│   ├── taskService.ts   # 任务服务
│   ├── resultService.ts # 结果服务
│   ├── reportService.ts # 报告服务
│   └── drugLibService.ts # 药物库服务
├── stores/              # Zustand 状态管理
│   ├── authStore.ts     # 认证状态
│   ├── taskStore.ts     # 任务状态
│   └── uiStore.ts       # UI 状态
├── hooks/               # 自定义 Hooks
│   └── useSSE.ts        # SSE 实时推送 Hook
├── types/               # TypeScript 类型定义
│   └── index.ts
└── utils/               # 工具函数
```

## 页面列表

| 页面 | 路由 | 权限 | 说明 |
|------|------|------|------|
| Dashboard | /dashboard | 所有用户 | 系统概览、统计卡片、最近任务 |
| 创建任务 | /tasks/new | 所有用户 | SMILES/SDF 输入、靶点选择、参数配置 |
| 任务管理 | /tasks | 所有用户 | 任务列表、筛选、搜索 |
| 任务详情 | /tasks/:jobId | 所有用户 | Agent 执行链路、SSE 实时进度 |
| Agent 监控 | /monitor | PI/Admin | 执行统计、节点记录 |
| Docking 结果 | /results/docking | 所有用户 | Top Hits 列表、药物搜索、详情 |
| 结构可视化 | /results/structure | 所有用户 | 3D 蛋白结构、结合位点 |
| AI 分析 | /results/ai-analysis | 所有用户 | AI 分析结果、追问对话 |
| 报告中心 | /reports | 所有用户 | 报告列表、PDF 预览/下载 |
| 药物库管理 | /drug-library | Admin | 药物统计、CSV 导入、药物详情 |

## 角色权限 (RBAC)

| 角色 | 权限 |
|------|------|
| Researcher | 创建/查看任务、查看结果、下载报告 |
| PI (项目负责人) | Researcher 权限 + Agent 监控 |
| Admin | 全部权限，包括药物库管理 |

## API 对接

后端 API 基础路径: `http://localhost:8000/api/v1`

主要接口:
- `POST /auth/login` - JWT 登录
- `POST /auth/register` - 注册
- `POST /jobs` - 创建筛选任务
- `GET /jobs/{id}` - 查询任务状态
- `GET /jobs/{id}/events` - SSE 任务进度推送
- `GET /jobs/{id}/results` - 查询 Docking 结果
- `GET /jobs/{id}/analysis` - AI 分析结果
- `GET /jobs/{id}/report/download` - 下载报告
- `GET /drugs` - 药物库查询
