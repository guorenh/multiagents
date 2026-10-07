import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, Optional, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_tools.registry import MCPRegistry



class MCPClientManager:
    def __init__(self, registry: MCPRegistry):
        self._registry = registry
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack: Dict[str, AsyncExitStack] = {}

    async def start_server(self, name:str):
        config = self._registry.get_server(name=name)
        if not config:
            raise ValueError(f"服务'{name}'不存在")
        import os
        env = config.get("env") or dict(os.environ)
        if config["transport"] == "stdio":
            params = StdioServerParameters(
                command=config["command"],
                args=config["args"],
                env=env,
            )
            stack = AsyncExitStack()
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            self._sessions[name] = session
            self._exit_stack[name] = stack
            self._registry.set_status(name, "running")

    async def call_tool(self, server: str, tool: str, args: dict):
        if server not in self._sessions:
            raise RuntimeError(f"服务'{server}'未启动")
        session = self._sessions[server]
        return await session.call_tool(tool, args)

    async def stop_server(self, name: str):
        if name in self._exit_stack:
            await self._exit_stack[name].aclose()
            del self._exit_stack[name]
            del self._sessions[name]
            self._registry.set_status(name, "stopped")
    async def start_all(self):
        for server in self._registry.list_servers():
            name = server["name"]
            try:
                await self.start_server(name)
            except Exception as e:
                print(f"Failed to start server '{name}': {e}")
                self._registry.set_status(name, "error")

    async def stop_all(self):
        for name in list(self._sessions.keys()):
            try:
                await self.stop_server(name)
            except Exception as e:
                print(f"Failed to stop server '{name}': {e}")
                self._registry.set_status(name, "error")
    async def list_tools(self, server: str):
        if server not in self._sessions:
            raise RuntimeError(f"服务'{server}'未启动")
        session = self._sessions[server]
        result = await session.list_tools()
        return result.tools

    async def list_all_tools(self):
        all_tools = []
        for name in self._sessions.keys():
            try:
                tools = await self.list_tools(name)
                for tool in tools:
                    all_tools.append({
                        "server":name,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema":  getattr(tool, "inputSchema", getattr(tool, "input_schema", {})),
                    })
            except Exception as e:
                print(f"获取服务'{name}'的工具信息失败: {e}")
        return all_tools

    async def close(self):
        await self.stop_all()