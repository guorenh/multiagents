from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from langgraph.graph.message import add_messages


class ResearchState(TypedDict):
    # 调研主题
    topic: str
    # supervisor 规划的检索关键词列表
    plan: List[str]
    # 对话历史
    messages: Annotated[List[Dict[str, Any]], add_messages]
    # 搜索历史记录
    search_history: List[Dict[str, Any]]
    # 积累的原始文本数据
    raw_data: str
    # 结构化分析结果
    analysis: Dict[str, Any]
    # 报告草稿(Markdown)
    draft: str
    # 审查评分(0-100)，未评分为 None
    review_score: Optional[int]
    # 审查意见，供 reporter 改写时参考
    review_feedback: str
    # 改写轮次计数，初始为 0
    iteration: int
    # 当前步骤指示
    next_step: Literal["search", "analyze", "review", "report", "finish"]
    error: Optional[str]
