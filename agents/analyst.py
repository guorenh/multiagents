import json
from graph.state import ResearchState
from utils.config_loader import Config


def create_analyst_node(manager, tools, llm):
    """
    创建分析器节点(闭包注入依赖)
    """
    config = Config()
    analyst_persona = config.agent("analyst")

    async def analyst_node(state: ResearchState) -> dict:
        """
        分析器节点
        """
        topic = state["topic"]
        raw_data = state.get("raw_data", "")

        if not raw_data:
            return {"error": "没有原始数据可供分析"}
        system_prompt = f"""你是{analyst_persona["role"]}。
{analyst_persona["backstory"]}。
你的目标{analyst_persona["goal"]}。

请以以下原始数据，输出一个JSON格式的分析结果，
 JSON对象必须包含以下字段：
- "market_size": 市场规模描述
- "key_players": 主要参与者描述
- "trends": 市场趋势描述
- "opportunities": 机会列表
- "risks": 风险列表
只输出JSON对象，不要输出其他文本。"""
        user_prompt = f"调研主题: {topic}\n\n原始数据: {raw_data[:3000]}。\n\n请分析并输出JSON格式的分析结果。"
        response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        ])
        analysis_text = response.content
        # 清理可能存在的代码块标记
        if analysis_text.startswith("```"):
            analysis_text = analysis_text.split("```")[1]
            if analysis_text.startswith("json"):
                analysis_text = analysis_text[4:]
            analysis_text = analysis_text.strip()

        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            # 解析失败，存原始文本
            analysis = {"raw": analysis_text}
        return {"analysis": analysis}
    return analyst_node
