import os
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_tools.registry import MCPRegistry



class MCPClientManager:
    def __init__(self, registry: MCPRegistry):
        self._registry = registry
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stacks: Dict[str, AsyncExitStack] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task = None 

    @property
    def running_servers(self) -> List[str]:
        """当前已建立会话的服务名列表"""
        return list(self._sessions.keys())

    def start_worker(self):
        """在 lifespan 里调用，启动管理任务"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def _dispatch(self, op: str, args: Any, direct) -> None:
        """把操作派发给 worker 串行执行。

        兜底：若 worker 未启动（忘记调用 start_worker），就直接执行，
        而不是把 future 丢进无人消费的队列里永久等待。
        """
        if self._worker_task is None:
            await direct(args)
            return
        future = asyncio.get_running_loop().create_future()
        await self._queue.put((op, args, future))
        await future

    async def _worker(self):
        """后台任务：串行处理所有 MCP 操作"""
        while True:
            op, args, future = await self._queue.get()
            try:
                if op == "start":
                    await self._do_start(args)
                elif op == "stop":
                    await self._do_stop(args)
                elif op == "restart_all":
                    await self._do_restart_all()
                elif op == "stop_all":
                    await self.stop_all()
                future.set_result(True)
            except Exception as e:
                future.set_exception(e)
            finally:
                self._queue.task_done()
    async def _do_start(self, name:str):
        config = self._registry.get_server(name=name)
        if not config:
            raise ValueError(f"服务'{name}'不存在")
        if name in self._sessions:
            return
        env = config.get("env") or dict(os.environ)
        if config["transport"] != "stdio":
            raise NotImplementedError(
                f"暂不支持 transport='{config['transport']}'（服务'{name}'），目前仅实现 stdio"
            )
        params = StdioServerParameters(
            command=config["command"],
            args=config["args"],
            env=env,
        )
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except BaseException:
            # 启动失败必须回收子进程，否则会留下孤儿进程
            await stack.aclose()
            self._registry.set_status(name, "error")
            raise

        self._sessions[name] = session
        self._exit_stacks[name] = stack
        self._registry.set_status(name, "running")
    async def start_server(self, name: str):
        """对外接口：发命令给 worker"""
        await self._dispatch("start", name, self._do_start)
    async def call_tool(self, server: str, tool: str, args: dict):
        if server not in self._sessions:
            raise RuntimeError(f"服务'{server}'未启动")
        session = self._sessions[server]
        return await session.call_tool(tool, args)

    async def _do_stop(self, name: str):
        """实际停止逻辑（只在 worker task 里执行）"""
        if name in self._exit_stacks:
            await self._exit_stacks[name].aclose()
            del self._exit_stacks[name]
            del self._sessions[name]
            self._registry.set_status(name, "stopped")
    async def stop_server(self, name: str):
        """对外接口：发命令给 worker"""
        await self._dispatch("stop", name, self._do_stop)

    async def restart_all(self):
        """对外接口：重启所有服务（Key 变更后调用）"""
        await self._dispatch("restart_all", None, lambda _: self._do_restart_all())

    async def _do_restart_all(self):
        """重启所有服务（Key 变更后调用）"""
        for name in list(self._exit_stacks.keys()):
            await self._do_stop(name)
        for server in self._registry.list_servers():
            await self._do_start(server["name"]) 
    async def start_all(self):
        for server in self._registry.list_servers():
            name = server["name"]
            try:
                await self._do_start(name)
            except Exception as e:
                print(f"Failed to start server '{name}': {e}")
                self._registry.set_status(name, "error")

    async def stop_all(self):
        for name in list(self._sessions.keys()):
            try:
                await self._do_stop(name)
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
        """关闭所有服务并停止 worker。未启动 worker 时也能安全调用。"""
        if self._worker_task is None:
            await self.stop_all()
            return

        await self._dispatch("stop_all", None, lambda _: self.stop_all())

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None