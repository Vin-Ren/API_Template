
from ..api.api import API


class BasePlugin:
    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.api.__getattribute__(name)
    
    def __init__(self, api: API):
        self.api = api
