
from types import NoneType
from typing import Callable, Dict

from ..data_structs import ReprCustomMapping

from ..plugins.base import BasePlugin


class ReprMixin:
    _repr_format = "<%(classname)s object>" # Format of __repr__
    
    def __repr__(self):
        return self.__class__._repr_format % ReprCustomMapping.get_instance(self)


class PluggableMixin:
    PLUGINS: Dict[str, BasePlugin] = []
    
    def __getitem__(self, name):
        return self._plugins.__getitem__(name)
    
    def __init__(self, *args, **kwargs):
        self._plugins = {name: plugin(self) for name, plugin in self.__class__.PLUGINS.items()}
        super().__init__(*args, **kwargs)


class LogGetattrMixin:
    LOGGER_FUNCTION: Callable[[str], NoneType] = print
    def __getattribute__(self, name: str):
        value = super().__getattribute__(name)
        cls = super().__getattribute__('__class__')
        cls.LOGGER_FUNCTION("%(classname)s.__getattribute__(%(repr)s,'%(name)s') -> %(value)s" % dict(classname=cls.__name__, repr=super().__getattribute__('__repr__')(), name=name, value=value))
        return value
