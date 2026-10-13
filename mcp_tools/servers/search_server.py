import os
from dotenv import load_dotenv
from tavily import TavilyClient
from mcp.server.mcpserver import MCPServer

load_dotenv()

mcp = MCPServer("market-research-server")

@mcp.tool()
def search_market(query: str, max_results: int = 5) -> str:
    """搜索市场情报，返回标题、链接和摘要"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "ERROR:TAVILY_API_KEY_MISSING: 请先在设置中配置 Tavily API Key"
    tavily_client = TavilyClient(api_key=api_key)
    max_results = min(max_results, 10)
    
    try:
        response = tavily_client.search(query, max_results=max_results)
        results = response.get("results", [])
        
        if not results:
            return "未找到相关结果"
        
        formatted_results = []
        for result in results:
            formatted_results.append(
                f"标题: {result.get('title', '无标题')}\n"
                f"链接: {result.get('url', '无链接')}\n"
                f"摘要: {result.get('content', '无摘要')}\n"
            )
        
        return "\n".join(formatted_results)
    
    except Exception as e:
        return f"搜索出错: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")