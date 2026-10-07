import asyncio
from mcp_tools.registry import MCPRegistry
from mcp_tools.client import MCPClientManager


async def main():
    registry = MCPRegistry()
    
    # 如果还没注册，先注册
    if "search" not in registry.list_servers():
        registry.register(
            name="search",
            transport="stdio",
            description="市场情报搜索",
            command="python",
            args=["-m", "mcp_tools.servers.search_server"],
        )
    
    manager = MCPClientManager(registry)
    
    # 启动
    await manager.start_server("search")
    print("状态:", registry.get_status("search"))
    
    # 列出工具
    tools = await manager.list_all_tools()
    print("工具列表:", tools)
    
    # 调用工具
    result = await manager.call_tool("search", "search_market", {"query": "新能源汽车 市场趋势", "max_results": 3})
    print("搜索结果:", result)
    
    # 停止
    await manager.stop_server("search")
    print("停止后状态:", registry.get_status("search"))


if __name__ == "__main__":
    asyncio.run(main())