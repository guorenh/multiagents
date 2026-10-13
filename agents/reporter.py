import json

from graph.state import ResearchState
from utils.config_loader import Config


def create_reporter_node(manager, tools, llm):
    config = Config()
    reporter_persona = config.agent("reporter")

    async def reporter_node(state: ResearchState) -> dict:
        topic = state["topic"]
        analysis = state.get("analysis", {})

        if not analysis:
            return {"error": "没有分析结果可供撰写"}

        system_prompt = f"""你是{reporter_persona["role"]}。
{reporter_persona["backstory"]}。
你的目标{reporter_persona["goal"]}。
请根据以下分析结果，撰写一篇完整的调研报告，报告应包含以下内容：
- 调研主题
- 市场规模描述
- 主要参与者描述
- 市场趋势描述
- 机会列表
- 风险列表
请以专业、客观的语气撰写报告，确保内容准确、清晰，并且逻辑连贯。
报告格式采用markdown，使用标题、段落和列表等结构化元素。
具体参考：
# [调研主题] 市场调研报告

## 一、市场规模
...

## 二、主要参与者
...

## 三、市场趋势
...

## 四、机会与风险
...

## 五、结论与建议
...
"""

        user_prompt = (
            f"调研主题: {topic}\n\n"
            f"分析结果: {json.dumps(analysis, ensure_ascii=False, indent=2)}。\n\n"
            f"请撰写完整的调研报告。"
        )

        # 如果是审校后的改写，带上上一版和审查意见
        previous = state.get("draft", "")
        feedback = state.get("review_feedback", "")
        is_rewrite = bool(previous) and state.get("review_score") is not None

        if is_rewrite:
            user_prompt += (
                f"\n\n这是第 {state.get('iteration', 0) + 1} 次改写。"
                f"\n上一版报告：\n{previous[:4000]}\n"
                f"\n审查意见（必须逐条修正）：\n{feedback or '（无具体意见，请整体提升质量）'}\n"
                f"\n请输出改进后的完整报告，不要只输出修改片段。"
            )
            system_prompt += "\n注意：必须直接回应审查意见，不要重复上一版存在的问题。"

        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        report = response.content

        updates = {
            "draft": report,
            # 重置评分，让 supervisor 重新走一轮审查
            "review_score": None,
        }
        if is_rewrite:
            updates["iteration"] = state.get("iteration", 0) + 1

        return updates

    return reporter_node
