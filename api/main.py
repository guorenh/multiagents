import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import research, mcp, config
from api.services import research_service
from utils import key_store

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# 这些前缀属于后端 API，不能被前端 SPA 的兜底路由吞掉
API_PREFIXES = ("/research", "/mcp", "/config", "/health", "/docs", "/redoc", "/openapi.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 顺序要紧：先把 .env 迁移进 credentials.json，再把后者同步到环境变量。
    # inject_to_environ 会清掉 credentials 中已不存在的键，所以必须放在迁移之后。
    key_store.migrate_from_env()
    key_store.inject_to_environ()
    await research_service.init_research_app()
    try:
        yield
    finally:
        # 关闭时回收 MCP 子进程
        await research_service.shutdown()


app = FastAPI(title="市场调研助手 API", version="0.1.0", lifespan=lifespan)

# 开发环境下前端跑在 vite(5173)，直连后端时需要 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(mcp.router)
app.include_router(config.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# 托管前端构建产物（存在才挂载）。
# 注意：必须注册在 API 路由之后，否则兜底路由会抢走 API 请求。
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 未命中的后端路由仍然返回 404，不要伪装成前端页面。
        # 只拦截"前缀 + 子路径"，因为 /mcp 这类裸路径本身就是前端页面路由。
        for prefix in API_PREFIXES:
            name = prefix.strip("/")
            if full_path.startswith(name + "/"):
                raise HTTPException(status_code=404, detail="Not Found")

        candidate = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)

        # 其余路径交给前端路由（BrowserRouter 需要 index.html 兜底）
        return FileResponse(os.path.join(DIST_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    # 只监听本机回环地址：接口没有鉴权，/config/keys 谁都能改，
    # 绑 0.0.0.0 会把改 Key 和烧 API 额度的能力暴露给整个局域网。
    # 确实需要从别的机器访问时，用 `--host 0.0.0.0` 显式启动，并自行加鉴权。
    uvicorn.run(app, host="127.0.0.1", port=8000)
