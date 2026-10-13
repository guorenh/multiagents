import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, Optional

from runtime import ResearchRuntime
from utils import key_store

logger = logging.getLogger(__name__)

# 任务表：有容量上限，避免长跑后把历史报告全文常驻内存
MAX_TASKS = 100
TASK_TTL_SECONDS = 60 * 60  # 完成超过 1 小时的任务可被清理

tasks: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

# 持有后台任务的强引用：事件循环只持弱引用，
# 不保存引用会导致任务在执行中被 GC 回收、静默中断
_inflight: set[asyncio.Task] = set()

_runtime: Optional[ResearchRuntime] = None


async def init_research_app() -> None:
    global _runtime
    _runtime = await ResearchRuntime().setup()
    logger.info("调研应用初始化完成，工具：%s", [t.name for t in _runtime.tools])


async def shutdown() -> None:
    """关闭时回收 MCP 子进程，避免留下孤儿进程"""
    global _runtime
    if _runtime is not None:
        await _runtime.close()
        _runtime = None
        logger.info("调研应用已关闭")


def get_runtime() -> Optional[ResearchRuntime]:
    return _runtime


def _evict_tasks() -> None:
    """按 TTL 和容量上限清理已完成任务"""
    now = time.time()
    for task_id, task in list(tasks.items()):
        if task["status"] in ("completed", "failed"):
            finished_at = task.get("finished_at") or now
            if now - finished_at > TASK_TTL_SECONDS:
                tasks.pop(task_id, None)

    while len(tasks) > MAX_TASKS:
        # 优先淘汰已结束的任务
        for task_id, task in tasks.items():
            if task["status"] in ("completed", "failed"):
                tasks.pop(task_id, None)
                break
        else:
            break  # 全在跑，不再淘汰


def create_task(topic: str) -> str:
    """创建调研任务，返回 task_id"""
    task_id = str(uuid.uuid4())

    _evict_tasks()
    tasks[task_id] = {
        "status": "running",
        "topic": topic,
        "report": "",
        "error": None,
        "created_at": time.time(),
        "finished_at": None,
    }

    task = asyncio.create_task(_run_research(task_id, topic))
    # 保存强引用，防止任务被垃圾回收
    _inflight.add(task)
    task.add_done_callback(_inflight.discard)

    return task_id


async def _run_research(task_id: str, topic: str) -> None:
    """后台执行调研任务"""
    entry = tasks.get(task_id)
    try:
        if _runtime is None:
            raise RuntimeError("调研应用未初始化")

        result = await _runtime.run(topic)

        if entry is not None:
            entry["report"] = result.get("draft", "")
            entry["error"] = result.get("error")
            entry["status"] = "failed" if result.get("error") else "completed"
            entry["finished_at"] = time.time()

    except asyncio.CancelledError:
        if entry is not None:
            entry["error"] = "任务已取消"
            entry["status"] = "failed"
            entry["finished_at"] = time.time()
        raise
    except Exception as e:
        logger.exception("调研任务失败 task_id=%s", task_id)
        if entry is not None:
            entry["error"] = str(e)
            entry["status"] = "failed"
            entry["finished_at"] = time.time()


def get_task(task_id: str) -> Optional[dict]:
    """查询任务状态"""
    return tasks.get(task_id)


def get_registry():
    return _runtime.registry if _runtime else None


def get_manager():
    return _runtime.manager if _runtime else None


async def rebuild_app() -> None:
    """Key 变更后重建 MCP 服务 + LLM + 图"""
    if _runtime is None:
        raise RuntimeError("应用未初始化")
    await _runtime.rebuild()
    logger.info("应用已重建")


def get_keys_status() -> list:
    return key_store.get_keys_status()


def get_missing_keys() -> list:
    return key_store.get_missing_keys()
