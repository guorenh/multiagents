import os
import sys
from contextlib import asynccontextmanager

# 支持 `python api/main.py` 直接运行。
# 直接跑脚本时 sys.path[0] 是 api/ 而不是项目根目录，
# 下面的 `from api.routes import ...` 会 ModuleNotFoundError。
# 注意这段必须放在包导入之前。
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from api.routes import research, mcp, config  # noqa: E402
from api.services import research_service  # noqa: E402
from utils import key_store  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# 这些前缀属于后端 API，不能被前端 SPA 的兜底路由吞掉。
# 必须包含 /api：否则请求一个不存在的 /api/xxx 会拿到 index.html（200 + HTML），
# 前端把 HTML 当数据解析，报出 "xxx.map is not a function" 这种莫名其妙的错。
API_PREFIXES = (
    "/api",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


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

    # 默认只监听回环地址：接口没有鉴权，/config/keys 谁都能改，
    # 绑 0.0.0.0 会把改 Key、烧 API 额度的能力暴露给整个局域网。
    #
    # 容器里必须绑 0.0.0.0 才能被端口映射到，此时用 compose 的
    # `127.0.0.1:8000:8000` 把暴露面收回到宿主机本机。
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
