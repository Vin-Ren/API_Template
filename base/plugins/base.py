
from ..api.api import API


class _BasePlugin:
    ENABLE_GETITEM_VARIABLE_ACCESS = False
    
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.api.__getattribute__(name)
    
    def __getitem__(self, name):
        if self.__class__.ENABLE_GETITEM_VARIABLE_ACCESS:
            return self.__getattribute__(name)
        else:
            return super().__getitem__(name)
    
    def __init__(self, api: API):
        self.api = api

class BasePlugin(_BasePlugin):
    def __getattribute__(self, name: str):
        return super().__getattribute__(name)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
