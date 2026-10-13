import os
import json

KEYS_SCHEMA = {
    "OPENAI_API_KEY": {
        "label": "LLM API Key",
        "description": "调用大模型用，兼容 OpenAI 格式（DeepSeek/通义/Kimi 等均可）",
        "required": True,
        "used_by": ["analyst", "reporter", "supervisor"],
        "url": "https://platform.deepseek.com",
        "secret": True,
    },
    "OPENAI_BASE_URL": {
        "label": "LLM API 端点",
        "description": "模型服务的 base_url，如 https://api.deepseek.com",
        "required": True,
        "used_by": ["analyst", "reporter", "supervisor"],
        "url": "",
        "secret": False,
    },
    "LLM_MODEL": {
        "label": "LLM 模型",
        "description": "留空则使用 config.yaml 中的默认值。可下拉选择，也可直接输入任意模型名",
        "required": False,
        "used_by": ["analyst", "reporter", "supervisor", "reviewer"],
        "url": "",
        "secret": False,
        # type=select 时前端用「可搜索 + 允许自由输入」的 AutoComplete 渲染
        "type": "select",
        # 本机实测可用的模型名（网关接受的远比 /models 接口返回的多）
        "options": [
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "deepseek-flash",
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v4-flash-vision-exp",
        ],
        "placeholder": "留空使用 config.yaml 默认值",
    },
    "TAVILY_API_KEY": {
        "label": "Tavily 搜索 Key",
        "description": "网络搜索用",
        "required": True,
        "used_by": ["searcher"],
        "url": "https://tavily.com",
        "secret": True,
    },
}

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "..", "data/credentials.json")

def _load_credentials() -> dict:
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[key_store] 读取凭证失败: {e}")
        return {}


def _save_credentials(credentials: dict):
    dir_name = os.path.dirname(CREDENTIALS_FILE)
    os.makedirs(dir_name, exist_ok=True)
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(credentials, f, indent=4, ensure_ascii=False)

def get_keys_status() -> list:
    creds = _load_credentials()
    result = []
    for name, meta in KEYS_SCHEMA.items():
        result.append({
            "name": name,
            **meta,
            "is_configured": bool(creds.get(name)),
        })
    return result

def set_key(name: str, value: str) -> None:
    """写入配置。

    非必填项传入空字符串表示「清空」，回落到 config.yaml 的默认值
    （例如 LLM_MODEL 清空后就用 config.yaml 里的 model_name）。
    必填项不允许清空——静默抹掉 API Key 会造成很难排查的运行期故障。
    """
    if name not in KEYS_SCHEMA:
        raise ValueError(f"未知的 Key: {name}")

    if value == "":
        if KEYS_SCHEMA[name]["required"]:
            raise ValueError(f"{KEYS_SCHEMA[name]['label']} 是必填项，不能清空")
        creds = _load_credentials()
        creds.pop(name, None)
        _save_credentials(creds)
        os.environ.pop(name, None)
        return

    creds = _load_credentials()
    creds[name] = value
    _save_credentials(creds)
    os.environ[name] = value

def get_key(name: str) -> str | None:
    return os.environ.get(name) or _load_credentials().get(name)

def get_missing_keys() -> list:
    creds = _load_credentials()
    return [
        name for name, meta in KEYS_SCHEMA.items()
        if meta["required"] and not creds.get(name)
    ]

def inject_to_environ() -> None:
    """把 credentials.json 同步到环境变量。

    必须处理「被删掉的键」：只做覆盖的话，os.environ 里会残留旧值，
    导致清空 LLM_MODEL 之类的操作看起来没生效。
    """
    creds = _load_credentials()
    for name in KEYS_SCHEMA:
        if name in creds:
            os.environ[name] = creds[name]
        else:
            os.environ.pop(name, None)

def migrate_from_env() -> None:
    """首次启动时，把 .env 里的 Key 迁移到 credentials.json"""
    from dotenv import load_dotenv
    load_dotenv()
    creds = _load_credentials()
    changed = False
    for name in KEYS_SCHEMA:
        if not creds.get(name) and os.environ.get(name):
            creds[name] = os.environ[name]
            changed = True
    if changed:
        _save_credentials(creds)
        print(f"[key_store] 已从 .env 迁移 {len([k for k in KEYS_SCHEMA if creds.get(k)])} 个 Key")