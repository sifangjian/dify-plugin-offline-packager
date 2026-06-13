# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY frontend/ .
RUN npm run build

# Stage 2: Runtime
FROM python:3.12-slim

# Install uv via pip (avoids slow ghcr.io download)
RUN pip install --no-cache-dir uv -i https://mirrors.aliyun.com/pypi/simple

WORKDIR /app

# Install Python dependencies (without the project itself)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend code (includes dify-plugin CLI binaries in backend/app/)
COPY backend/ backend/

# Copy frontend build output
COPY --from=frontend-build /app/frontend/dist/ frontend/dist/

# Create workspace directory for packaging tasks
RUN mkdir -p /app/workspace

WORKDIR /app/backend

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/api/v1/health')" || exit 1

# 使用 shell 形式以支持环境变量
CMD /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
