import os
from langchain_openai import ChatOpenAI
from utils.config_loader import Config

def get_llm() -> ChatOpenAI:
    config = Config()
    llm_config = config.llm
    return ChatOpenAI(
        model=llm_config["model_name"],
        temperature=llm_config["temperature"],
        base_url=llm_config["base_url"],
        api_key=os.environ.get("OPENAI_API_KEY")
    )

