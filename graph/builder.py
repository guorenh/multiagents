from langgraph.graph import StateGraph, START, END
from graph.state import ResearchState
from agents.analyst import create_analyst_node
from agents.reporter import create_reporter_node
from agents.reviewer import create_reviewer_node
from agents.searcher import create_searcher_node
from agents.supervisor import create_supervisor_node


def route_supervisor(state: ResearchState) -> str:
    """条件边路由函数：根据 next_step 决定走向"""
    return state.get("next_step", "finish")


def build_graph(manager, tools, llm):
    graph = StateGraph(ResearchState)

    graph.add_node("searcher", create_searcher_node(manager, tools))
    graph.add_node("analyst", create_analyst_node(manager, tools, llm))
    graph.add_node("reporter", create_reporter_node(manager, tools, llm))
    graph.add_node("reviewer", create_reviewer_node(manager, tools, llm))
    graph.add_node("supervisor", create_supervisor_node(llm))

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
            "review": "reviewer",
            "finish": END,
        },
    )

    # 所有专家节点执行完，回到 supervisor
    graph.add_edge("searcher", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("reporter", "supervisor")
    graph.add_edge("reviewer", "supervisor")

    return graph.compile()
