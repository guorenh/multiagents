import asyncio
import time
from mcp_tools.registry import MCPRegistry
from mcp_tools.client import MCPClientManager
from mcp_tools.adapters import convert_all_tools
from utils.llm import get_llm
from graph.builder import build_graph


async def main():
    t0 = time.time()
    print(f"[{time.time()-t0:.1f}s] 0. 开始执行 main()")

    print(f"[{time.time()-t0:.1f}s] 1. 获取 Registry...")
    registry = MCPRegistry()
    print(f"[{time.time()-t0:.1f}s] 1. Registry 就绪")

    names = [s["name"] for s in registry.list_servers()]
    print(f"[{time.time()-t0:.1f}s] 2. 已有服务: {names}")
    if "search" not in names:
        registry.register(
            name="search",
            transport="stdio",
            description="市场调研工具",
            command="python",
            args=["-m", "mcp_tools.servers.search_server"],
        )
        print(f"[{time.time()-t0:.1f}s] 2. 已注册 search 服务")

    print(f"[{time.time()-t0:.1f}s] 3. 创建 Manager...")
    manager = MCPClientManager(registry)

    print(f"[{time.time()-t0:.1f}s] 4. 启动 search 服务...")
    await manager.start_server("search")
    print(f"[{time.time()-t0:.1f}s] 4. search 服务已启动")

    print(f"[{time.time()-t0:.1f}s] 5. 转换工具...")
    tools = await convert_all_tools(manager)
    print(f"[{time.time()-t0:.1f}s] 5. 工具已转换: {[t.name for t in tools]}")

    print(f"[{time.time()-t0:.1f}s] 6. 初始化 LLM...")
    llm = get_llm()
    print(f"[{time.time()-t0:.1f}s] 6. LLM 就绪")

    print(f"[{time.time()-t0:.1f}s] 7. 构建图...")
    app = build_graph(manager, tools, llm)
    print(f"[{time.time()-t0:.1f}s] 7. 图已构建")

    initial_state = {
        "topic": "新能源汽车市场",
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

    print(f"[{time.time()-t0:.1f}s] 8. 开始执行图（预计 30-90 秒）...")
    result = await app.ainvoke(initial_state)
    print(f"[{time.time()-t0:.1f}s] 8. 图执行完成")

    print("=" * 60)
    print("调研报告")
    print("=" * 60)
    print(result["draft"])
    if result.get("error"):
        print("错误:", result["error"])

    print(f"[{time.time()-t0:.1f}s] 9. 停止服务...")
    await manager.stop_server("search")
    print(f"[{time.time()-t0:.1f}s] 9. 服务已停止")


if __name__ == "__main__":
    asyncio.run(main())