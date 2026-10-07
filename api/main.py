from fastapi import FastAPI
from api.routes import research
from api.services.research_service import init_research_app
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_research_app()
    yield
    # 关闭时（可选：停止 MCP 服务）

app = FastAPI(title="市场调研助手 API", version="0.1.0", lifespan=lifespan)
app.include_router(research.router)



@app.get("/health")
async def health():
    return {"status": "ok"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)