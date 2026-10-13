import json

from graph.state import ResearchState
from utils.config_loader import Config

PLAN_PROMPT = """你是一位市场调研总监。请把下面的调研主题拆解成{max_q}条以内的中文检索关键词。

要求：
- 每条关键词都要能直接丢进搜索引擎
- 覆盖不同侧面（如市场规模、主要厂商、技术路线、政策、风险）
- 不要写成问句，不要加编号，不要输出任何解释

只输出一个 JSON 数组，例如：["关键词1", "关键词2"]

调研主题：{topic}"""


def _parse_plan(text: str, limit: int) -> list:
    """尽力从模型输出里解析出关键词列表，失败返回空列表。"""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(q).strip() for q in data if str(q).strip()][:limit]


def create_supervisor_node(llm=None):
    """创建监督者节点。

    控制流保持确定性（保证一定能终止），但检索规划交给 LLM，
    让 supervisor 真正承担"拆解问题、调度专家"的职责。
    """
    config = Config()
    min_score = config.min_score
    max_iterations = config.max_iterations
    max_queries = config.max_search_queries

    async def _make_plan(topic: str) -> list:
        if llm is None:
            return [topic]
        try:
            resp = await llm.ainvoke([
                {"role": "user", "content": PLAN_PROMPT.format(topic=topic, max_q=max_queries)},
            ])
            plan = _parse_plan(resp.content, max_queries)
        except Exception as e:
            print(f"[supervisor] 规划检索关键词失败，回退为主题本身: {e}")
            plan = []
        # 规划失败时退化成一个查询，保证流程继续
        return plan or [topic]

    async def supervisor_node(state: ResearchState) -> dict:
        # 出错时直接结束
        if state.get("error"):
            return {"next_step": "finish"}

        # 硬保险：无论上游怎么设置，迭代次数超过上限就收工，
        # 保证图一定收敛（正常流程永远碰不到这条分支）
        if state.get("iteration", 0) > max_iterations + 2:
            return {"next_step": "finish"}

        updates = {}

        # 1. 首次进入时规划检索关键词
        if not state.get("plan"):
            updates["plan"] = await _make_plan(state["topic"])

        # 2. 确定性路由（顺序即优先级，保证流程必然收敛）
        if not state.get("raw_data"):
            next_step = "search"
        elif not state.get("analysis"):
            next_step = "analyze"
        elif not state.get("draft"):
            next_step = "report"
        elif state.get("review_score") is None:
            next_step = "review"
        elif (
            state["review_score"] < min_score
            and state.get("iteration", 0) < max_iterations
        ):
            # 评分不达标且还有改写额度 → 退回 reporter 重写
            next_step = "report"
        else:
            next_step = "finish"

        updates["next_step"] = next_step
        return updates

    return supervisor_node
