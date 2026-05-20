# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dify Plugin Offline Packager — a web tool to search Dify Marketplace plugins, download them with all Python dependencies, and produce offline `.difypkg` bundles. Full-stack: Python FastAPI backend + Vue 3 frontend, communicating via SSE for real-time packaging progress.

## Development Commands

### Backend (from project root)
```bash
uv sync                                          # Install dependencies
cd backend && uv run uvicorn app.main:app --reload --port 8080  # Dev server
uv run ruff check .                               # Lint
uv run ruff check --fix .                         # Lint fix
uv run ruff format .                              # Format
uv run ruff format --check .                      # Format check
uv run pytest                                     # Run all tests
uv run pytest backend/tests/test_services/test_packager.py  # Single test file
```

### Frontend (from `frontend/`)
```bash
npm install          # Install dependencies
npm run dev          # Dev server on :3000 (proxies /api and /sse to :8080)
npm run build        # Production build to frontend/dist/
npm run typecheck    # TypeScript type checking
npm run lint         # ESLint check + fix
npm run test         # Vitest run
npm run test:watch   # Vitest watch mode
```

## Architecture

### Backend (`backend/app/`)

**Dependency direction:** `api/ → services/ → models/`, `api/ → core/`, `services/ → core/`. Never import in reverse.

- **`main.py`** — FastAPI app entry. Mounts static files and SPA fallback for production.
- **`core/config.py`** — `Settings` via pydantic-settings. All config from env vars / `.env`. Access via `get_settings()`.
- **`core/lifespan.py`** — Initializes httpx client, StorageService, PackagerService on startup; cleans up on shutdown. Services stored on `app.state`.
- **`core/exceptions.py`** — `AppException` hierarchy and global FastAPI exception handlers.
- **`api/`** — Three routers aggregated in `api/router.py`:
  - `marketplace.py` — Proxies search/category/detail to Dify Marketplace API
  - `pack.py` — Submit packaging sessions, upload local plugins, download results, cancel
  - `sse.py` — SSE endpoint for real-time packaging progress
- **`services/packager.py`** — Core orchestrator. Producer-consumer pattern via `asyncio.Queue`:
  1. `submit_session()` creates tasks per plugin and enqueues them
  2. `_queue_consumer()` processes tasks sequentially
  3. For marketplace plugins: download → resolve deps → download deps → package
  4. For local plugins: resolve deps → download deps → package
  5. Each step emits SSE events to subscribers
  - Uses `_run_subprocess_with_progress()` for pip and dify-plugin CLI, with throttled (200ms) progress callbacks
- **`services/marketplace.py`** — HTTP client wrapper for Dify Marketplace API
- **`services/storage.py`** — Manages per-task directory structure under `WORK_DIR`:
  ```
  workspace/{task_id}/
  ├── source/     # Downloaded .difypkg files
  ├── plugin/     # Extracted plugin + wheels/ for deps
  └── output/     # Generated offline .difypkg
  ```
- **`models/`** — Pydantic v2 models: `marketplace.py`, `plugin.py` (PackStep/TaskStatus enums), `sse.py` (event types)

### Frontend (`frontend/src/`)

**Dependency direction:** `views/ → components/, stores/, composables/`, `stores/ → api/ → types/`. Never import in reverse.

- **Views:** `SearchView` (main browse/search), `UploadView` (local plugin upload), `PackageView` (packaging progress + download), `PluginDetailView`
- **Stores (Pinia):** `marketplace` (search/categories/pagination), `cart` (selected plugins), `packager` (packaging session state)
- **Composables:** `useSSE` — EventSource connection with auto-reconnect
- **API layer:** `client.ts` (axios instance), `marketplace.ts`, `plugin.ts`
- **Styling:** Tailwind CSS 4 only. No custom CSS, no `@apply`, no inline styles.

### Key External Tools

- **`dify-plugin` CLI** (`DIFY_PLUGIN_CLI_PATH`) — Used for `plugin package` command to create offline bundles
- **`uv`** — Used at runtime for `uv lock` + `uv export` when plugins only have `pyproject.toml`
- **`pip download`** — Downloads wheel dependencies from configurable PyPI mirror (`PIP_MIRROR_URL`)

## Code Conventions

- **Language:** UI text and commit messages in Chinese; code identifiers in English
- **Python:** All public functions need type annotations, all I/O must be async, use `httpx` not `requests`
- **TypeScript:** `import type` for type-only imports, `interface` for objects, `type` for unions, no `any`
- **Vue:** `<script setup lang="ts">` only (no Options API), component order: script → template → style scoped
- **Commit format:** Conventional Commits with Chinese subject: `feat(scope): 添加插件搜索功能`
- **Tests:** pytest with `asyncio_mode = "auto"` in backend; Vitest + happy-dom + Vue Test Utils in frontend
- **Ruff config:** target py312, line-length 120, double quotes, space indent
