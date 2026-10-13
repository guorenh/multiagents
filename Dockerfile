# syntax=docker/dockerfile:1

# 镜像源。国内直连 pypi.org / registry.npmjs.org 经常只有几十 kB/s 甚至超时，
# 所以默认走国内镜像。海外环境或想用官方源，覆盖这两个 build arg 即可：
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG NPM_REGISTRY=https://registry.npmmirror.com

# ============================================================
# 阶段 1：构建前端
# ============================================================
FROM node:24-alpine AS frontend

ARG NPM_REGISTRY
WORKDIR /app/frontend

# 先只拷贝依赖清单，利用层缓存：只要 lock 文件没变就不会重装依赖
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=$NPM_REGISTRY --fetch-retries=5 --fetch-retry-maxtimeout=120000

COPY frontend/ ./
RUN npm run build


# ============================================================
# 阶段 2：运行时
# ============================================================
FROM python:3.12-slim

ARG PIP_INDEX_URL
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

COPY requirements.txt ./
RUN pip install --no-cache-dir \
        --index-url $PIP_INDEX_URL \
        --timeout 120 \
        --retries 5 \
        -r requirements.txt

COPY . ./

# 前端构建产物来自阶段 1，不依赖宿主机上有没有 dist/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# 容器内必须监听 0.0.0.0 才能被端口映射到；
# 对外暴露面由 compose 的 `127.0.0.1:8000:8000` 收回到宿主机本机。
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000

EXPOSE 8000

# /health 不依赖 API Key，缺 Key 时服务也能起来并返回 200
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["python", "-m", "api.main"]
