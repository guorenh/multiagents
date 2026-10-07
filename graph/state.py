from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from langgraph.graph.message import add_messages

class ResearchState(TypedDict):
    #调研主题
    topic: str 
    #规划节点输入的任务列表
    plan: List[str] 
    #对话历史
    messages: Annotated[List[Dict[str, Any]], add_messages]
    #搜索历史记录
    search_history: List[Dict[str, Any]] 
    #积累的原始文本数据
    raw_data: str
    #结构化分析结果
    analysis: Dict[str, Any]
    #报告草稿(Markdown)
    draft: str
    #审查评分(0-100)可空
    review_score: Optional[int]
    #迭代计数初始为0
    iteration: int 
    #当前步骤指示，可选"search"/"analyze"/"review"/"report"/"finish"
    next_step: str = Literal["search","analyze","review","report","finish"]
    error: Optional[str]
