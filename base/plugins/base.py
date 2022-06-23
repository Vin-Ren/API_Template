
from typing import Any, Union, List, Dict

from ..data_structs import ObjectifiedDict, Config
from ..helper.class_mixin import ReprMixin


class _BasePlugin(ReprMixin):
    ENABLE_GETITEM_VARIABLE_ACCESS = False
    REQUIRED_CONFIGS: Dict[str, Any] = {} # A dictionary of required config entries of the plugin. with form as such: {'config name': config default value}. e.g: {'retry_count': 3}
    
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
    
    def __init__(self, api):
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
    REQUIRED_CONFIGS: Dict[str, Any] = {} # For additional configuration the api might need
    
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
    
    def __init_subclass__(cls):
        if isinstance(cls.PLUGINS, dict):
            # Updating plugins
            if cls.INHERIT_PLUGINS:
                plugins = {}
                [plugins.update(current_cls_plugins) for current_cls_plugins in reversed([_cls.PLUGINS for _cls in cls.mro() if issubclass(_cls, PluggableMixin) and isinstance(_cls.PLUGINS, dict)])]
                cls.PLUGINS = plugins
            
            cls._plugins = {name: plugin(cls) for name, plugin in cls.PLUGINS.items()}
        else:
            # Updating plugins
            if cls.INHERIT_PLUGINS:
                plugins = []
                [plugins.extend(current_cls_plugins) for current_cls_plugins in reversed([_cls.PLUGINS for _cls in cls.mro() if issubclass(_cls, PluggableMixin) and isinstance(_cls.PLUGINS, list)])]
                cls.PLUGINS = list(set(plugins))
            
            if cls.PLUGINS_ACCESSIBLE_THROUGH_INSTANCE_VARIABLE:
                cls._plugins = {plugin.__name__: plugin(cls) for plugin in cls.PLUGINS}
            else:
                cls._plugins = {plugin: plugin(cls) for plugin in cls.PLUGINS}
        
        cls._plugins = ObjectifiedDict(cls._plugins)
        cls._required_configs = Config({name: default for plugin in cls._plugins for name, default in plugin.REQUIRED_CONFIGS.keys()})
        cls._required_configs.update(cls.REQUIRED_CONFIGS)
        cls.__pluggable_mixin_cached_method_table = {}

    @classmethod
    def get_required_config_fields(cls):
        return list(cls._required_configs.keys())

    @classmethod
    def get_basic_config(cls):
        return cls._required_configs
