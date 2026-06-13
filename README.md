# Dify Plugin Offline Packager

将 [Dify](https://github.com/langgenius/dify) 插件打包成离线安装包的 Web 工具。搜索 Marketplace 插件或上传本地插件，选择目标架构，一键生成包含所有 Python 依赖的离线 `.difypkg` 包。

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Vue-3.5+-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue" />
  <img src="https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Vite-8.0+-646CFF?logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-4.0+-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/Docker-多阶段构建-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

## 功能特性

- **Marketplace 浏览** — 关键词搜索、分类筛选、集合浏览，查看插件详情
- **本地上传** — 上传 `.difypkg` 文件，解析插件信息后直接打包
- **离线打包** — 自动下载插件及全部 Python 依赖，生成离线安装包
- **多架构支持** — 支持 `linux-amd64`、`linux-arm64`、`darwin-amd64`、`darwin-arm64`
- **实时进度** — 通过 SSE 流式展示打包各步骤的实时进度
- **依赖兼容性处理** — 自动替换 PyPI 上不可用的依赖版本，提高打包成功率
- **一体化工作台** — 左右分栏布局，边搜索边查看打包进度

## 快速开始

### 方式一：docker-compose（推荐）

```bash
# 克隆仓库
git clone git@github.com:sifangjian/dify-plugin-offline-packager.git
cd dify-plugin-offline-packager/

# 复制配置文件
cp .env.example .env

# 根据需要修改配置（可选）
# vim .env

# 构建并启动
docker-compose up -d
```

浏览器访问 `http://localhost:8080` 即可使用。

### 方式二：docker run

```bash
# 克隆仓库
git clone git@github.com:sifangjian/dify-plugin-offline-packager.git
cd dify-plugin-offline-packager/

# 构建镜像
docker build -t dify-plugin-offline-packager .

# 启动服务
docker run -p 8080:8080 dify-plugin-offline-packager
```

浏览器访问 `http://localhost:8080` 即可使用。

自定义配置：

```bash
# 克隆仓库
git clone git@github.com:sifangjian/dify-plugin-offline-packager.git
cd dify-plugin-offline-packager/

# 构建镜像
docker build -t dify-plugin-offline-packager .

# 启动服务
docker run -p 9090:9090 \
  -e PORT=9090 \
  -e PIP_MIRROR_URL=https://pypi.org/simple \
  -v ./workspace:/app/workspace \
  dify-plugin-offline-packager
```

## 使用说明

1. **搜索插件** — 在左侧面板的搜索框中输入关键词，或通过分类/集合浏览插件
2. **选择架构** — 点击插件卡片上的「打包」按钮，选择目标架构
3. **查看进度** — 右侧任务面板实时显示打包进度，支持取消和重试
4. **下载结果** — 打包完成后自动下载离线包，文件名格式为 `{name}-{version}-{architecture}-offline.difypkg`
5. **上传本地插件** — 切换到「本地上传」标签页，拖拽或选择 `.difypkg` 文件上传后打包

### 安装离线包

1. 访问 Dify 平台的 **插件管理页面**
2. 选择 **通过本地插件文件安装**
3. 上传对应的 `*-linux-amd64.difypkg`（x86_64 服务器）或 `*-linux-arm64.difypkg`（ARM64 服务器）文件
4. 完成安装后即可在应用中启用

### Dify 平台配置（离线环境）

在 `.env` 配置文件中添加/修改以下字段：

```bash
# 允许安装未在 Marketplace 审核的插件
FORCE_VERIFYING_SIGNATURE=false

# 允许安装 500M 以内的插件
PLUGIN_MAX_PACKAGE_SIZE=524288000

# Nginx 允许上传 500M 以内的内容
NGINX_CLIENT_MAX_BODY_SIZE=500M
```

## 配置

通过环境变量或 `.env` 文件配置，所有配置项均有默认值，开箱即用。完整配置参见 [.env.example](.env.example)。

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MARKETPLACE_API_URL` | `https://marketplace.dify.ai` | Dify Marketplace API 地址 |
| `PIP_MIRROR_URL` | `https://mirrors.aliyun.com/pypi/simple` | pip 下载镜像源 |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8080` | 服务监听端口 |
| `MAX_UPLOAD_SIZE_MB` | `500` | 最大上传文件大小（MB） |
| `UPLOAD_EXPIRE_HOURS` | `24` | 上传文件过期时间（小时） |
| `WORK_DIR` | `/app/workspace` | 打包工作目录 |

## License

[MIT](LICENSE)
