
from typing import Union, List, Dict

from ..data_structs import ObjectifiedDict
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


class PluggableMixin:
    PLUGINS: Union[List[BasePlugin], Dict[str, BasePlugin]] = []
    PLUGINS_ACCESSIBLE_THROUGH_INSTANCE_VARIABLE = False
    ENABLE_DIRECT_GETATTR_PLUGINS_ACCESS = False
    INHERIT_PLUGINS = True
    
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError as exc:
            if self.__class__.PLUGINS_ACCESSIBLE_THROUGH_INSTANCE_VARIABLE:
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
                [plugins.update(current_cls_plugins) for current_cls_plugins in reversed([cls.PLUGINS for cls in self.__class__.mro() if issubclass(cls, self.__class__) and isinstance(cls.PLUGINS, dict)])]
                self.__class__.PLUGINS = plugins
            
            self._plugins = {name: plugin(self) for name, plugin in self.__class__.PLUGINS.items()}
        else:
            # Updating plugins
            if self.__class__.INHERIT_PLUGINS:
                plugins = []
                [plugins.extend(current_cls_plugins) for current_cls_plugins in reversed([cls.PLUGINS for cls in self.__class__.mro() if issubclass(cls, self.__class__) and isinstance(cls.PLUGINS, list)])]
                self.__class__.PLUGINS = list(set(plugins))
            
            if self.__class__.PLUGINS_ACCESSIBLE_THROUGH_INSTANCE_VARIABLE:
                self._plugins = {plugin.__name__: plugin(self) for plugin in self.__class__.PLUGINS}
            else:
                self._plugins = {plugin: plugin(self) for plugin in self.__class__.PLUGINS}
        super().__init__(*args, **kwargs)
        self._plugins = ObjectifiedDict(self._plugins)
        self.__pluggable_mixin_cached_method_table = {}
