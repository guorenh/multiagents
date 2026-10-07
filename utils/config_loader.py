import os
import yaml
from dotenv import load_dotenv
from typing import Optional, Dict, Any

class Config:
    def __init__(self, path: Optional[str] = None):
        load_dotenv()
        
        if path is None:
            self.path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        else:
            self.path = path

        self._data = None

    def _load(self) -> Dict[str, Any]:
        if self._data is None:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f)
        return self._data

    @property
    def llm(self):
        return self._load()["llm"]

    def agent(self, name: str):
        return self._load()["agents"][name]
    
    @property
    def max_iterations(self):
        return self._load().get("max_iterations", 5)
    
