# Dify Plugin Offline Packager

Dify 插件离线打包工具 — 打开浏览器，搜索插件，一键打包下载离线包。

## 快速开始

### Docker 部署（推荐）

```bash
docker build -f docker/Dockerfile -t dify-plugin-offline-packager .
docker run -p 8080:8080 dify-plugin-offline-packager
```

浏览器访问 `http://localhost:8080` 即可使用。

### 开发环境

**后端**：

```bash
uv sync
uv run uvicorn backend.app.main:app --reload --port 8080
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`，自动代理 API 请求到后端。

## 环境变量

参见 [.env.example](.env.example) 获取所有可配置项。

## 技术栈

- **后端**：Python 3.12 + FastAPI + uvicorn + httpx
- **前端**：Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia
- **通信**：SSE (Server-Sent Events)
- **部署**：Docker 多阶段构建

## License

MIT
