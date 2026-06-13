# Dify Plugin Offline Packager — 开发指南

> 本文件为开发参考，不提交到 Git。面向用户的 README.md 已另行维护。

## 项目概述

将 Dify 插件打包成离线安装包的 Web 工具。搜索 Marketplace 插件或上传本地插件，选择目标架构，一键生成包含所有 Python 依赖的离线 `.difypkg` 包。

**核心流程**：搜索/上传插件 → 选择架构 → 后端异步打包（下载→解析依赖→下载依赖→打包）→ SSE 实时推送进度 → 自动下载离线包

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Python + FastAPI + uvicorn | 3.12 + 0.115+ |
| 前端框架 | Vue 3 + Composition API | 3.5+ |
| 类型系统 | TypeScript | 6.0+ |
| 构建工具 | Vite | 8.0+ |
| CSS 方案 | Tailwind CSS | 4.0+ |
| 状态管理 | Pinia | 2.3+ |
| HTTP 客户端（前端） | axios | 1.16+ |
| HTTP 客户端（后端） | httpx | 0.28+ |
| 数据校验 | pydantic + pydantic-settings | 2.0+ |
| 实时通信 | SSE (Server-Sent Events) | — |
| 代码质量 | ruff（后端）+ ESLint（前端） | — |
| 包管理 | uv（后端）+ npm（前端） | — |
| 部署 | Docker 多阶段构建 | — |

## 本地开发

### 后端

```bash
uv sync                                                                # 安装依赖
cd backend && uv run uvicorn app.main:app --reload --port 8080         # 开发服务器
uv run ruff check .                                                    # Lint
uv run ruff check --fix .                                              # Lint 修复
uv run ruff format .                                                   # 格式化
uv run pytest backend/tests/                                           # 全部测试
uv run pytest backend/tests/test_services/test_packager.py             # 单个文件
```

### 前端

```bash
cd frontend
npm install                                                            # 安装依赖
npm run dev                                                            # 开发服务器 :3000（代理 /api /sse → :8080）
npm run build                                                          # 生产构建 → frontend/dist/
npm run typecheck                                                      # TypeScript 类型检查
npm run lint                                                           # ESLint 检查 + 修复
npm run test                                                           # Vitest 运行
npm run test:watch                                                     # Vitest 监听模式
```

前端开发时，Vite dev server 代理 `/api/*` 和 `/sse/*` 请求到后端 `localhost:8080`。

### Docker

```bash
docker build -f docker/Dockerfile -t dify-plugin-offline-packager .
docker run -p 8080:8080 dify-plugin-offline-packager
```

## 架构设计

### 后端（`backend/app/`）

**依赖方向**：`api/ → services/ → models/`，`api/ → core/`，`services/ → core/`。反向禁止。

```
backend/app/
├── main.py                    # FastAPI 入口，挂载静态文件 + SPA 回退
├── api/                       # API 路由层
│   ├── router.py              # 路由汇总注册 + /health
│   ├── marketplace.py         # Marketplace 搜索/浏览/详情
│   ├── pack.py                # 打包提交/取消/下载
│   ├── upload.py              # 本地插件文件上传
│   └── sse.py                 # SSE 流式推送
├── core/                      # 核心基础设施
│   ├── config.py              # pydantic-settings 配置（环境变量 + .env）
│   ├── exceptions.py          # 自定义异常 + 全局处理器
│   └── lifespan.py            # 启动/关闭生命周期（httpx, StorageService, 定时清理）
├── models/                    # Pydantic 数据模型
│   ├── marketplace.py         # 插件搜索结果、详情、分类
│   ├── plugin.py              # 打包请求/任务/状态、上传模型、架构枚举
│   └── sse.py                 # SSE 事件类型
└── services/                  # 业务逻辑层
    ├── marketplace.py         # httpx 封装调用 Dify Marketplace API
    ├── packager.py            # 打包核心：asyncio.Queue 生产者-消费者模式
    ├── plugin_parser.py       # 解析 .difypkg 中的 manifest.yaml
    └── storage.py             # 任务目录管理 + 上传文件存储/过期清理
```

**打包流程**（`services/packager.py`）：

1. `submit_session()` 为每个插件创建任务并入队
2. `_queue_consumer()` 逐个处理任务
3. Marketplace 插件：下载 → 解析依赖 → 下载依赖 → 打包
4. 本地插件：解析依赖 → 下载依赖 → 打包
5. 每个步骤通过 SSE 推送事件给订阅者

**关键外部工具**：

- `dify-plugin` CLI — `plugin package` 命令创建离线包，每个架构一个二进制文件
- `uv` — 运行时调用 `uv lock` + `uv export` 解析 pyproject.toml 依赖
- `pip download` — 下载 wheel 包，支持 `--platform` 指定目标架构

### 前端（`frontend/src/`）

**依赖方向**：`views/ → components/, stores/, composables/`，`stores/ → api/ → types/`。反向禁止。

```
frontend/src/
├── App.vue                    # 根组件
├── main.ts                    # 入口
├── router/index.ts            # 路由（hash 模式）
├── views/                     # 页面
│   ├── WorkspaceView.vue      # 一体化工作台（左右分栏）
│   └── PluginDetailView.vue   # 插件详情页
├── components/                # 组件
│   ├── SplitPane.vue          # 可拖拽分栏容器
│   ├── SearchPanel.vue        # 左侧面板（Tab: 在线搜索/本地上传）
│   ├── TaskPanel.vue          # 右侧打包任务面板
│   ├── PluginCard.vue         # 插件卡片
│   ├── PluginCardSkeleton.vue # 骨架屏
│   ├── PackageLog.vue         # SSE 日志流
│   ├── CategoryFilter.vue     # 分类筛选
│   ├── ArchitectureSelector.vue # 架构选择对话框
│   └── NavBar.vue             # 顶部导航栏
├── stores/                    # Pinia 状态管理
│   ├── marketplace.ts         # 搜索/分类/分页
│   └── packager.ts            # 打包任务、上传管理、队列
├── api/                       # API 封装
│   ├── client.ts              # axios 实例 + 拦截器
│   ├── marketplace.ts         # searchPlugins, getCollections, getPluginDetail, batchGetPlugins
│   └── plugin.ts              # uploadPlugins, startPack, cancelSession, getDownloadUrl
├── composables/
│   └── useSSE.ts              # EventSource 连接管理 + 自动重连
├── types/
│   ├── marketplace.ts         # Plugin, SearchResult, CollectionsResult
│   ├── packager.ts            # PackTaskProgress, Architecture, SSEEvent
│   └── upload.ts              # UploadResponse, BatchUploadResponse
└── assets/styles/
    └── main.css               # Tailwind CSS 入口
```

### 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | WorkspaceView | 首页，一体化工作台 |
| `/plugin/:author/:name` | PluginDetailView | 插件详情页 |

### API 路由

| 前缀 | 模块 | 端点 |
|------|------|------|
| `/api/v1/marketplace` | marketplace.py | `POST /search`, `GET /collections`, `GET /{author}/{name}` |
| `/api/v1/plugins` | pack.py | `POST /pack`, `POST /cancel/{session_id}`, `GET /download/{task_id}` |
| `/api/v1/plugins` | upload.py | `POST /upload` |
| `/api/v1/sse` | sse.py | `GET /pack/{session_id}` |
| `/api/v1/health` | router.py | `GET /health` |

### 数据流

```
浏览器
  ├── 搜索/浏览 → api/marketplace.ts → api/marketplace.py → services/marketplace.py → Dify Marketplace API
  ├── 上传插件  → api/plugin.ts      → api/upload.py      → services/storage.py + plugin_parser.py
  ├── 启动打包  → api/plugin.ts      → api/pack.py        → services/packager.py → asyncio 子进程
  │                                                         composables/useSSE.ts ← api/sse.py ← SSE 事件流
  └── 下载结果  → api/plugin.ts      → api/pack.py        → services/storage.py
```

## 配置

通过环境变量或 `.env` 文件配置。完整配置参见 [.env.example](.env.example)。

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MARKETPLACE_API_URL` | `https://marketplace.dify.ai` | Dify Marketplace API 地址 |
| `PIP_MIRROR_URL` | `https://mirrors.aliyun.com/pypi/simple` | pip 下载镜像源 |
| `GITHUB_API_URL` | `https://github.com` | GitHub API（预留） |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8080` | 服务监听端口 |
| `MAX_UPLOAD_SIZE_MB` | `500` | 最大上传文件大小（MB） |
| `UPLOAD_EXPIRE_HOURS` | `24` | 上传文件过期时间（小时） |
| `WORK_DIR` | `/app/workspace` | 打包工作目录 |
| `STATIC_DIR` | `frontend/dist` | 前端静态文件目录 |
| `DEPENDENCY_VERSION_PATCHES` | `{...}` | 依赖版本替换映射 |
| `DEPENDENCY_REMOVAL_LIST` | `["xhtml2pdf", ...]` | 需移除的依赖包 |

## 代码规范

- **语言**：UI 文本和 commit message 用中文，代码标识符用英文
- **Python**：公共函数需要 type hints，I/O 必须 async，用 `httpx` 不用 `requests`
- **TypeScript**：`import type` 导入类型，`interface` 定义对象，`type` 定义联合类型，禁止 `any`
- **Vue**：只用 `<script setup lang="ts">`，组件顺序：script → template → style scoped
- **CSS**：只用 Tailwind CSS，不写自定义 CSS、不用 `@apply`、不用内联样式
- **Commit**：Conventional Commits 中文主题，如 `feat(pack): 添加架构选择功能`
- **测试**：后端 pytest（asyncio_mode=auto），前端 Vitest + happy-dom + Vue Test Utils
- **Ruff**：target py312, line-length 120, 双引号, 空格缩进
