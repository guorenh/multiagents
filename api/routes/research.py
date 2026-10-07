from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services import research_service

router = APIRouter(prefix="/research", tags=["research"])

class ResearchRequest(BaseModel):
    topic: str

@router.post("")
async def create_research(req: ResearchRequest):
    task_id = research_service.create_task(req.topic)
    return {"task_id": task_id, "status": "running"}
    
@router.get("/{task_id}")
async def get_research_status(task_id: str):
    task = research_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "task_id": task_id,
        "status": task["status"],
        "topic": task["topic"],
        "error": task["error"],
    }

@router.get("/{task_id}/report")
async def get_research_report(task_id: str):
    task = research_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="报告尚未生成")
    return {"report": task["report"]}