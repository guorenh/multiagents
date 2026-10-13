from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services import research_service
from utils import key_store

router = APIRouter(prefix="/api/config", tags=["config"])

class KeysUpdate(BaseModel):
    # 字段名 -> 值；值传空字符串表示清空（非必填项回落到 config.yaml 默认值）
    keys: Dict[str, str]

@router.get("/keys")
async def list_keys():
    return research_service.get_keys_status()

@router.post("/keys")
async def update_keys(req: KeysUpdate):
    """批量保存配置。

    重建会重启 MCP 服务（拉起子进程），代价很高，
    所以先全部写完再统一重建一次，而不是每个字段重建一次。
    """
    # 注意：req.keys 是字段本身（一个 dict），不是 dict.keys() 方法
    updates = req.keys
    if not updates:
        return {"status": "ok", "saved": []}

    try:
        for name, value in updates.items():
            key_store.set_key(name, value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await research_service.rebuild_app()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存成功但重建失败: {str(e)}")

    return {"status": "ok", "saved": list(updates)}

@router.get("/status")
async def get_config_status():
    """返回配置是否就绪、缺失的 Key，以及当前实际生效的模型。

    ready 的判断依据是"图能不能跑"，而不只是"Key 填了没有"——
    填了 Key 但构建失败时，前端也应该继续停在设置页。
    """
    missing = research_service.get_missing_keys()
    runtime = research_service.get_runtime()

    model = None
    try:
        from utils.llm import get_llm
        model = get_llm().model_name
    except Exception:
        # Key 还没配全时拿不到实例，不影响就绪状态判断
        pass

    graph_ready = bool(runtime and runtime.ready)

    return {
        "ready": len(missing) == 0 and graph_ready,
        "missing_keys": missing,
        "model": model,
        "graph_ready": graph_ready,
        "error": runtime.last_error if runtime else None,
    }
