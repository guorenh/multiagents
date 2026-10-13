import asyncio

from mcp_tools.registry import MCPRegistry
from mcp_tools.client import MCPClientManager
from runtime import SEARCH_SERVER


async def main():
    registry = MCPRegistry()

    # 已注册则跳过（list_servers() 返回的是 dict 列表，不能直接和字符串比较）
    existing = [s["name"] for s in registry.list_servers()]
    if SEARCH_SERVER["name"] not in existing:
        registry.register(**SEARCH_SERVER)

    manager = MCPClientManager(registry)
    manager.start_worker()  # 不启动 worker，下面的 start_server 会一直等待

    try:
        await manager.start_server("search")
        print("状态:", registry.get_status("search"))

        tools = await manager.list_all_tools()
        print("工具列表:", tools)

        result = await manager.call_tool(
            "search", "search_market", {"query": "新能源汽车 市场趋势", "max_results": 3}
        )
        print("搜索结果:", result)
    finally:
        await manager.close()
        print("停止后状态:", registry.get_status("search"))


if __name__ == "__main__":
    asyncio.run(main())
