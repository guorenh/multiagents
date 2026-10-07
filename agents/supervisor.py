from graph.state import ResearchState

def create_supervisor_node(llm=None):
    """创建监督者节点"""
    
    async def supervisor_node(state: ResearchState) -> dict:
    # 出错时直接结束
        if state.get("error"):
            return {"next_step": "finish"}
    
        if not state.get("raw_data"):
            next_step = "search"
        elif not state.get("analysis"):
            next_step = "analyze"
        elif not state.get("draft"):
            next_step = "report"
        else:
            next_step = "finish"
    
        return {"next_step": next_step}
    return supervisor_node