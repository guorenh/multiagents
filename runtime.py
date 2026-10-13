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
        # 图构建失败的原因（通常是缺少 API Key），供 /config/status 展示
        self.last_error: str | None = None

    @property
    def ready(self) -> bool:
        return self.graph is not None

    async def _build_graph(self) -> None:
        """构建 LLM 与图。

        缺 API Key 时**不能**让异常冒泡：服务必须能起来，
        否则用户永远打不开设置页去填 Key（首次运行流程会直接死锁）。
        """
        try:
            self.graph = build_graph(self.manager, self.tools, get_llm(rebuild=True))
            self.last_error = None
        except Exception as e:
            self.graph = None
            self.last_error = str(e)
            logger.warning("图构建失败，服务仍会启动以便在设置页配置：%s", e)

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
        await self._build_graph()
        return self

    async def rebuild(self) -> None:
        """配置变更后重建 LLM 与图。

        MCP 服务只在确实在跑的时候才重启——首次启动时如果因为缺 Key
        还没连上，硬重启会把本已就绪的工具链一起搞坏。
        """
        if self.manager is None:
            raise RuntimeError("运行时尚未初始化")

        if self.manager.running_servers:
            await self.manager.restart_all()
            self.tools = await convert_all_tools(self.manager)

        await self._build_graph()

    async def run(self, topic: str) -> dict:
        if self.graph is None:
            raise RuntimeError(
                self.last_error or "调研应用未就绪，请先在设置页配置 API Key"
            )
        return await self.graph.ainvoke(initial_state(topic))

    async def close(self) -> None:
        if self.manager is not None:
            await self.manager.close()
            self.manager = None
