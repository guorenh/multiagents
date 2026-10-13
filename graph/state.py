from typing import TypedDict, List, Dict, Any, Optional, Literal


class ResearchState(TypedDict):
    # 调研主题
    topic: str
    # supervisor 规划的检索关键词列表
    plan: List[str]
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
    # 下一步走向。只由 supervisor 写入，其余节点不要设置
    next_step: Literal["search", "analyze", "review", "report", "finish"]
    error: Optional[str]
