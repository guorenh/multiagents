"""共享运行时：MCP 服务 + 工具 + LLM + LangGraph 图。

CLI(main.py) 和 API(api/services/research_service.py) 都从这里初始化，
避免两份 bootstrap 逻辑各自演化（之前 main.py 就是因为漏了一句
start_worker() 而永久卡死）。
"""
import logging

from mcp_tools.registry import MCPRegistry
from mcp_tools.client import MCPClientManager
from mcp_tools.adapters import convert_all_tools
from utils.llm import get_llm
from graph.builder import build_graph

logger = logging.getLogger(__name__)

SEARCH_SERVER = {
    "name": "search",
    "transport": "stdio",
    "description": "市场调研工具",
    "command": "python",
    "args": ["-m", "mcp_tools.servers.search_server"],
}


def initial_state(topic: str) -> dict:
    """图的初始状态，字段与 graph/state.py 的 ResearchState 保持一致"""
    return {
        "topic": topic,
        "plan": [],
        "messages": [],
        "search_history": [],
        "raw_data": "",
        "analysis": {},
        "draft": "",
        "review_score": None,
        "review_feedback": "",
        "iteration": 0,
        "next_step": "",
        "error": None,
    }


class ResearchRuntime:
    """持有 MCP 管理器与编译后的图，供 CLI / API 共用"""

    def __init__(self):
        self.registry: MCPRegistry | None = None
        self.manager: MCPClientManager | None = None
        self.tools: list = []
        self.graph = None

    async def setup(self) -> "ResearchRuntime":
        self.registry = MCPRegistry()

        names = [s["name"] for s in self.registry.list_servers()]
        if SEARCH_SERVER["name"] not in names:
            self.registry.register(**SEARCH_SERVER)
            logger.info("已注册 %s 服务", SEARCH_SERVER["name"])

        self.manager = MCPClientManager(self.registry)
        # 必须在任何 start_server 之前启动 worker，否则请求会无人消费
        self.manager.start_worker()

        await self.manager.start_server(SEARCH_SERVER["name"])
        self.tools = await convert_all_tools(self.manager)
        self.graph = build_graph(self.manager, self.tools, get_llm())
        return self

    async def rebuild(self) -> None:
        """Key 变更后重建 MCP 服务 + LLM + 图"""
        if self.manager is None:
            raise RuntimeError("运行时尚未初始化")
        await self.manager.restart_all()
        self.tools = await convert_all_tools(self.manager)
        self.graph = build_graph(self.manager, self.tools, get_llm(rebuild=True))

    async def run(self, topic: str) -> dict:
        if self.graph is None:
            raise RuntimeError("调研应用未初始化")
        return await self.graph.ainvoke(initial_state(topic))

    async def close(self) -> None:
        if self.manager is not None:
            await self.manager.close()
            self.manager = None
