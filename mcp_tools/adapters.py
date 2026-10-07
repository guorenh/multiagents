from typing import Any
from pydantic import create_model
from langchain_core.tools import StructuredTool
from mcp_tools.client import MCPClientManager

JSON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}

def _extract_text(result: Any) -> str:
    if result.content:
        return result.content[0].text
    return str(result)

def mcp_tool_to_langchain(tool_info: dict, manager: MCPClientManager) -> StructuredTool:
    """把 MCP 工具信息转换为 LangChain 的 StructuredTool"""
    server = tool_info["server"]
    name = tool_info["name"]
    description = tool_info["description"]
    schema = tool_info["input_schema"]

    fields = {}

    for prop_name, prop_info in schema.get("properties", {}).items():
        field_type = JSON_TYPE_MAP.get(prop_info.get("type"), str)
        required = prop_name in schema.get("required", [])
        default = ... if required else prop_info.get("default", None)
        fields[prop_name] = (field_type, default)

    ArgsSchema = create_model(f"{name}Args", **fields)

    async def _run(**kwargs):
        result = await manager.call_tool(server, name, kwargs)
        return _extract_text(result)

    return StructuredTool.from_function(
        coroutine=_run,
        name=name,
        description=description,
        args_schema=ArgsSchema,
    )

async def convert_all_tools(manager: MCPClientManager) -> list:
    """获取所有 MCP 工具并转换为 LangChain 格式"""
    tools_info = await manager.list_all_tools()
    return [mcp_tool_to_langchain(info, manager) for info in tools_info]