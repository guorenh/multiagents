from graph.state import ResearchState

def create_searcher_node(manager, tools):
    """
    创建搜索器节点(闭包注入依赖)
    """
    async def searcher_node(state: ResearchState):
        """
        搜索器节点
        """
        topic = state["topic"]

        search_tool = next((t for t in tools if t.name == "search_market"), None)
        if search_tool is None:
            return {"error": "搜索工具未找到", "next_step": "finish"}

        try:
            result = await search_tool.ainvoke({"query": topic, "max_results": 5})
            result = str(result) if not isinstance(result, str) else result
        except Exception as e:
            return {"error": f"搜索工具调用失败: {str(e)}", "next_step": "finish"}


        return {
            "raw_data": result,
            "search_history": state.get("search_history",[]) + [{"query": topic, "result": result[:500]}],
            "next_step": "analyze"
        }
    return searcher_node