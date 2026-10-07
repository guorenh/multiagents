import uuid
import asyncio
from typing import Dict, Any

from mcp_tools.registry import MCPRegistry
from mcp_tools.client import MCPClientManager
from mcp_tools.adapters import convert_all_tools
from utils.llm import get_llm
from graph.builder import build_graph

# 任务表
tasks: Dict[str, Dict[str, Any]] = {}

# 全局图实例（启动时构建一次）
_graph = None
_manager = None

async def init_research_app():
    """应用启动时初始化：启动 MCP 服务 + 构建图"""
    global _graph, _manager
    
    registry = MCPRegistry()
    
    # 1. 确保 search 服务已注册
    names = [s["name"] for s in registry.list_servers()]
    if "search" not in names:
        registry.register(
            name="search",
            transport="stdio",
            description="市场调研工具",
            command="python",
            args=["-m", "mcp_tools.servers.search_server"],
        )
    
    # 2. 创建 Manager 并启动服务
    _manager = MCPClientManager(registry)
    await _manager.start_server("search")
    
    # 3. 转换工具 + 构建图
    tools = await convert_all_tools(_manager)
    llm = get_llm()
    _graph = build_graph(_manager, tools, llm)
    
    print("✅ 调研应用初始化完成")

def create_task(topic: str) -> str:
    """创建调研任务，返回 task_id"""
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": "running",
        "topic": topic,
        "report": "",
        "error": None,
    }
    
    asyncio.create_task(_run_research(task_id, topic))
    return task_id

async def _run_research(task_id: str, topic: str):
    """后台执行调研任务"""
    try:
        if _graph is None:
            raise RuntimeError("调研应用未初始化")
        
        initial_state = {
            "topic": topic,
            "plan": [],
            "messages": [],
            "search_history": [],
            "raw_data": "",
            "analysis": {},
            "draft": "",
            "review_score": None,
            "iteration": 0,
            "next_step": "",
            "error": None,
        }
        
        result = await _graph.ainvoke(initial_state)
        
        tasks[task_id]["report"] = result.get("draft", "")
        tasks[task_id]["status"] = "completed"
        
    except Exception as e:
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["status"] = "failed"

def get_task(task_id: str) -> dict:
    """查询任务状态"""
    return tasks.get(task_id)