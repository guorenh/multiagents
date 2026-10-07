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
            return {"error": "没有分析结果可供撰写", "next_step": "finish"}
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

        user_prompt = f"调研主题: {topic}\n\n分析结果: {json.dumps(analysis, ensure_ascii=False, indent=2)}。\n\n请撰写完整的调研报告。"
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        report = response.content
        return {
            "draft": report,
            "next_step": "finish",
        }

    return reporter_node