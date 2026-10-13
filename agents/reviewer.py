import json

from graph.state import ResearchState
from utils.config_loader import Config

REVIEW_PROMPT = """你是{role}，负责给下属提交的调研报告打分。
{backstory}

第一步：判断这份报告是否真的在讲「调研主题」。跑题的典型表现是：
报告换了主体行业、答非所问、或写成了另一个话题的通用行业综述。

第二步：如果确实切题，再从以下维度给出 0-100 的整数总分：
1. 关键结论是否有数据支撑，数字是否被曲解
2. 结构是否完整（市场规模、主要参与者、趋势、机会、风险、结论）
3. 是否存在明显的事实编造或前后矛盾

只输出一个 JSON 对象，不要输出其他文本：
{{"on_topic": true, "score": 85, "feedback": "最需要改进的 1-3 点；若达标填 '无'"}}
若报告跑题，必须输出 {{"on_topic": false, "score": 0, "feedback": "说明跑题在哪里"}}"""


def _clean(text: str) -> str:
    return "".join(ch for ch in (text or "") if ch.isalnum())


def _lcs_length(a: str, b: str) -> int:
    """最长公共子串长度（滚动数组实现，内存 O(min(len(a), len(b))))"""
    if not a or not b:
        return 0
    if len(a) > len(b):
        a, b = b, a
    prev = [0] * (len(a) + 1)
    best = 0
    for ch in b:
        cur = [0] * (len(a) + 1)
        for i, ca in enumerate(a, 1):
            if ca == ch:
                cur[i] = prev[i - 1] + 1
                if cur[i] > best:
                    best = cur[i]
        prev = cur
    return best


def topic_coverage(topic: str, text: str) -> float:
    """主题在文本中的最长连续覆盖比例，用作跑题的确定性兜底信号。

    正常报告会原样带上主题（标题就是「[调研主题] 市场调研报告」），
    覆盖度接近 1；换成另一个行业的报告会明显偏低。
    """
    t = _clean(topic)
    if not t:
        return 1.0
    return _lcs_length(t, _clean(text)) / len(t)


# 低于该覆盖度即认定跑题，不采信模型的 on_topic 判断。
# 取 0.6：实测两次跑题报告分别为 0.38 / 0.50，而正常报告因为标题就是
# 「[调研主题] 市场调研报告」，覆盖度接近 1.0。误判的代价只是一次有界重做，
# 远小于"交付一份看起来正确、实则完全跑题的研报"。
COVERAGE_THRESHOLD = 0.6


def create_reviewer_node(manager, tools, llm):
    """创建审查节点：给报告草稿打分，跑题时触发整条链路重做"""
    config = Config()
    min_score = config.min_score
    max_iterations = config.max_iterations
    persona = config.agent("supervisor")

    async def reviewer_node(state: ResearchState) -> dict:
        draft = state.get("draft", "")
        topic = state["topic"]

        if not draft:
            return {"error": "没有报告草稿可供审查", "next_step": "finish"}

        system_prompt = REVIEW_PROMPT.format(
            role=persona["role"],
            backstory=persona["backstory"],
        )
        user_prompt = f"调研主题：{topic}\n\n报告全文：\n{draft[:6000]}"

        on_topic_by_llm = True
        score = min_score  # 评审失败时放行，避免死循环
        feedback = ""
        try:
            resp = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            text = (resp.content or "").strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            score = max(0, min(100, int(data["score"])))
            feedback = str(data.get("feedback", "")).strip()
            on_topic_by_llm = bool(data.get("on_topic", True))
        except Exception as e:
            print(f"[reviewer] 评分失败，按达标处理: {e}")
            return {"review_score": score, "review_feedback": ""}

        # 两个信号都通过才算切题：模型判断 + 确定性覆盖度
        coverage = topic_coverage(topic, draft)
        on_topic = on_topic_by_llm and coverage >= COVERAGE_THRESHOLD

        if on_topic:
            return {"review_score": score, "review_feedback": feedback}

        iteration = state.get("iteration", 0)
        print(f"[reviewer] 判定跑题（模型={on_topic_by_llm}, 主题覆盖度={coverage:.2f}）")

        if iteration >= max_iterations:
            # 改写额度已用尽：保留现有报告，但如实标记为不合格
            return {
                "review_score": 0,
                "review_feedback": f"已达重做上限，报告仍疑似跑题：{feedback}",
                "error": "报告未能收敛到调研主题（已用尽重做次数），结果可能不可靠",
            }

        # 跑题往往源于上游分析与主题脱节，只重写报告没用 → 丢弃整条链路结果，
        # 清空 plan 让 supervisor 重新规划检索词，从头跑一遍
        return {
            "plan": [],
            "raw_data": "",
            "analysis": {},
            "draft": "",
            "review_score": None,
            "review_feedback": "",
            "iteration": iteration + 1,
        }

    return reviewer_node
