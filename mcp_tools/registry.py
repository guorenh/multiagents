from typing import Any, Dict, List, Optional, Literal
import os
import yaml
class MCPRegistry:
    _instance: Optional["MCPRegistry"] = None

    def __new__(cls) -> "MCPRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_servers"):
            self._servers: Dict[str, Any] = {}
            self._config_path: str = os.path.join(os.path.dirname(__file__), "..", "mcp_server.yaml")
        self._load_from_file()

    def _load_from_file(self) -> None:
        if not os.path.exists(self._config_path):
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"servers": {}}, f)
            return
        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        servers = data.get("servers", {})
        for name, info in servers.items():
            self._servers[name] = {**info, "status": "registered"}

    def _save_to_file(self) -> None:
        data = {
            "servers":{
                name: {k: v for k, v in info.items() if k != "status"}
                for name, info in self._servers.items()
            }
        }
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def register(
            self, 
            name: str,
            transport: Literal["http", "stdio", "sse"],
            description: str = "",
            **params
    ) -> None:
        if name in self._servers:
            raise ValueError(f"Server with name '{name}' is already registered.")

        if transport not in [ "http", "stdio", "sse"]:
            raise ValueError(f"Invalid transport type '{transport}'. Must be 'http', 'stdio', or 'sse'.")

        if transport == "stdio":
            if "command" not in params:
                raise ValueError("For 'stdio' transport, 'command' parameter is required.")
            if "args" not in params:
                raise ValueError("For 'stdio' transport, 'args' parameter is required.")
        elif transport in ("http", "sse"):
            if "url" not in params:
                raise ValueError(f"For '{transport}' transport, 'url' parameter is required.")

        self._servers[name] = {
            **params,                    # 先展开用户参数
            "transport": transport,      # 再用固定字段覆盖
            "description": description,
            "status": "registered",
        }
        self._save_to_file()

    def unregister(self, name: str) -> bool:
        if name not in self._servers:
            return False
        if self._servers[name]["status"] == "running":
            raise RuntimeError(f"Cannot unregister server '{name}' while it is running.")
        del self._servers[name]
        self._save_to_file()
        return True

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        return self._servers.get(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, **info}
            for name, info in self._servers.items()
        ]

    def set_status(self, name: str, status: Literal["registered", "starting", "running", "stopping", "stopped", "error"]) -> bool:
        if name not in self._servers:
            raise ValueError(f"Server with name '{name}' is not registered.")
        self._servers[name]["status"] = status
        return True

    def get_status(self, name: str) -> Optional[str]:
        return self._servers.get(name, {}).get("status")

    def get_all_configs(self) -> Dict[str, Any]:
        return dict(self._servers)

    def clear(self) -> None:
        self._servers = {}
    
        