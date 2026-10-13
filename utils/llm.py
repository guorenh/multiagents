from langchain_openai import ChatOpenAI
from utils.config_loader import Config
from utils import key_store

_llm_instance = None

def get_llm(rebuild: bool = False) -> ChatOpenAI:
    """获取 LLM 实例，rebuild=True 时强制重建"""
    global _llm_instance
    
    if _llm_instance is not None and not rebuild:
        return _llm_instance
    
    config = Config()
    llm_config = config.llm
    
    # 优先从 key_store 读，回退到 config.yaml
    base_url = key_store.get_key("OPENAI_BASE_URL") or llm_config.get("base_url")
    api_key = key_store.get_key("OPENAI_API_KEY")
    
    model = key_store.get_key("LLM_MODEL") or llm_config["model_name"]

    if not api_key:
        raise ValueError("OPENAI_API_KEY 未配置，请在设置中填写")
    
    _llm_instance = ChatOpenAI(
        model=model,
        base_url=base_url,
        temperature=llm_config.get("temperature", 0.3),
        api_key=api_key,
    )
    return _llm_instance