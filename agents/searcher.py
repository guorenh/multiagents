import logging

from graph.state import ResearchState
from utils.config_loader import Config

logger = logging.getLogger(__name__)


def create_searcher_node(manager, tools):
    """创建搜索器节点(闭包注入依赖)"""
    config = Config()
    max_queries = config.max_search_queries

    async def searcher_node(state: ResearchState):
        """搜索器节点：按 supervisor 的 plan 逐条检索并汇总"""
        topic = state["topic"]
        plan = list(state.get("plan") or [topic])[:max_queries]

        search_tool = next((t for t in tools if t.name == "search_market"), None)
        if search_tool is None:
            return {"error": "搜索工具未找到"}

        chunks = []
        history = list(state.get("search_history", []))
        errors = []

        for query in plan:
            try:
                result = await search_tool.ainvoke({"query": query, "max_results": 5})
            except Exception as e:
                errors.append(f"{query}: {e}")
                logger.warning("检索失败 query=%r: %s", query, e)
                continue

            text = result if isinstance(result, str) else str(result)
            if not text.strip():
                errors.append(f"{query}: 返回为空")
                continue

            chunks.append(f"## 检索词：{query}\n{text}")
            history.append({"query": query, "result": text[:500]})

        # 所有检索词都失败才判定为失败；部分成功仍然继续
        if not chunks:
            return {"error": "全部检索均失败：" + "；".join(errors[:3])}

        return {
            "raw_data": "\n\n".join(chunks),
            "search_history": history,
        }

    return searcher_node
