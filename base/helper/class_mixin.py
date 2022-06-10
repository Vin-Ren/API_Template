
from types import NoneType
from typing import Callable, Dict, List, Union

from ..data_structs import ObjectifiedDict, ReprCustomMapping
from ..plugins.base import BasePlugin


class ReprMixin:
    _repr_format = "<%(classname)s object>" # Format of __repr__
    
    def __repr__(self):
        return self.__class__._repr_format % ReprCustomMapping.get_instance(self)


class PluggableMixin:
    PLUGINS: Union[List[BasePlugin], Dict[str, BasePlugin]] = []
    PLUGINS_ACCESSABLE_THROUGH_INSTANCE_VARIABLE = False
    ENABLE_DIRECT_GETATTR_PLUGINS_ACCESS = False
    INHERIT_PLUGINS = True
    
    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError as exc:
            if not self.__class__.PLUGINS_ACCESSABLE_THROUGH_INSTANCE_VARIABLE:
                pass

            try:
                return self.__getitem__(name)
            except KeyError as exc:
                pass

            if not self.__class__.ENABLE_DIRECT_GETATTR_PLUGINS_ACCESS:
                raise exc

            if name in self.__pluggable_mixin_cached_method_table:
                return self.__pluggable_mixin_cached_method_table[name]
            
            for plugin in self._plugins.values():
                try:
                    self.__pluggable_mixin_cached_method_table[name] = getattr(plugin, name)
                    return self.__pluggable_mixin_cached_method_table[name]
                except Exception as exc:
                    pass
            raise exc
    
    def __getitem__(self, name):
        return self._plugins.__getitem__(name)
    
    def __init__(self, *args, **kwargs):
        if isinstance(self.__class__.PLUGINS, dict):
            # Updating plugins
            if self.__class__.INHERIT_PLUGINS:
                plugins = {}
                [plugins.update(current_cls_plugin) for current_cls_plugin in reversed([cls.PLUGINS for cls in self.__class__.mro() if issubclass(cls, self.__class__) and isinstance(cls.PLUGINS, dict)])]
                self.__class__.PLUGINS = plugins
            
            self._plugins = {name: plugin(self) for name, plugin in self.__class__.PLUGINS.items()}
        else:
            # Updating plugins
            if self.__class__.INHERIT_PLUGINS:
                plugins = []
                [plugins.extend(current_cls_plugin) for current_cls_plugin in reversed([cls.PLUGINS for cls in self.__class__.mro() if issubclass(cls, self.__class__) and isinstance(cls.PLUGINS, list)])]
                self.__class__.PLUGINS = list(set(plugins))
            
            if self.__class__.PLUGINS_ACCESSABLE_THROUGH_INSTANCE_VARIABLE:
                self._plugins = {plugin.__name__: plugin(self) for plugin in self.__class__.PLUGINS}
            else:
                self._plugins = {plugin: plugin(self) for plugin in self.__class__.PLUGINS}
        super().__init__(*args, **kwargs)
        self._plugins = ObjectifiedDict(self._plugins)
        self.__pluggable_mixin_cached_method_table = {}


class LogGetattrMixin:
    LOGGER_FUNCTION: Callable[[str], NoneType] = print
    def __getattribute__(self, name: str):
        value = super().__getattribute__(name)
        cls = super().__getattribute__('__class__')
        cls.LOGGER_FUNCTION("%(classname)s.__getattribute__(%(repr)s,'%(name)s') -> %(value)s" % dict(classname=cls.__name__, repr=super().__getattribute__('__repr__')(), name=name, value=value))
        return value
