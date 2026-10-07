from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from graph.state import ResearchState
from agents.analyst import create_analyst_node
from agents.searcher import create_searcher_node
from agents.reporter import create_reporter_node
from agents.supervisor import create_supervisor_node

def route_supervisor(state: ResearchState) -> str:
    """条件边路由函数：根据 next_step 决定走向"""
    return state.get("next_step", "finish")

def build_graph(manager, tools, llm):
    print("  [builder] 1. 创建 StateGraph")
    graph = StateGraph(ResearchState)
    
    print("  [builder] 2. 创建 searcher 节点")
    graph.add_node("searcher", create_searcher_node(manager, tools))
    
    print("  [builder] 3. 创建 analyst 节点")
    graph.add_node("analyst", create_analyst_node(manager, tools, llm))
    
    print("  [builder] 4. 创建 reporter 节点")
    graph.add_node("reporter", create_reporter_node(manager, tools, llm))
    
    print("  [builder] 5. 创建 supervisor 节点")
    graph.add_node("supervisor", create_supervisor_node(llm))
    
    print("  [builder] 6. 添加边")
    # 入口指向 supervisor
    graph.add_edge(START, "supervisor")

    # supervisor 根据 next_step 条件路由
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "search": "searcher",
            "analyze": "analyst",
            "report": "reporter",
            "finish": END,
        },
    )

    # 所有专家节点执行完，回到 supervisor
    graph.add_edge("searcher", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("reporter", "supervisor")
    print("  [builder] 6. 编译图")
    compiled = graph.compile()
    print("  [builder] 7. 编译完成")
    
    return compiled