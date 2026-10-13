from fastapi import APIRouter, HTTPException
from api.services import research_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

@router.get("/servers")
async def get_mcp_servers():
    """
    Get a list of all available MCP servers.
    """
    registry = research_service.get_registry()
    if registry is None:
        raise HTTPException(status_code=404, detail="MCP registry not found")
    return registry.list_servers()

