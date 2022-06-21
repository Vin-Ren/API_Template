import io
import time

import requests


class ObjectifiedDict(dict):
    def __setattr__(self, name, value):
        return super().__setitem__(name, value)
    
    def __getattribute__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError:
            return super().__getattribute__(name)
    
    def __repr__(self):
        return '<{} object with {} field(s)>'.format(self.__class__.__name__, self.__len__())
    
    def update(self, other):
        for k,v in other.items():
            self.__setitem__(k,v)


class Config(ObjectifiedDict):
    pass


class Credential(ObjectifiedDict):
    pass


class Timer:
    def __init__(self, start_time=None):
        self.start_time = start_time
        self.current_time = None
        self.end_time = None
    
    @property
    def elapsed(self):
        return self.end_time-self.current_time if self.start_time is not None and self.current_time is not None else 0

    @property
    def duration(self):
        return self.end_time-self.end_time if self.start_time is not None and self.end_time is not None else 0
    
    @property
    def ended(self):
        return self.end_time is not None
    
    def start(self, explicit_time=None):
        self.start_time = (explicit_time if isinstance(explicit_time, (int, float)) else time.time())-1e-9
        return self
    
    def update_current(self, explicit_time=None):
        self.current_time = explicit_time if isinstance(explicit_time, (int, float)) else time.time()
        return self
    
    def end(self, explicit_time=None):
        self.end_time = explicit_time if isinstance(explicit_time, (int, float)) else time.time()
        return self


class ProgressInfo(ObjectifiedDict):
    def __init__(self, *, stream: requests.Response, pipe_handler: io.IOBase, time_info: Timer):
        super().__init__(stream=stream, pipe_handler=pipe_handler, time_info=time_info)
        self.stream: requests.Response
        self.pipe_handler: io.IOBase
        self.time_info: Timer
    
    def __bool__(self):
        return self.stream.ok
    
    @property
    def finished(self):
        return self.time_info.ended


class ReprCustomMapping:
    """
    Custom Mapping for the extensive use of ReprMixin.
    
    Provides the ability to access nested attributes. 
    Additionally, the use of eval is available and enabled by default for its functionality. This could be unsafe.
    The use of eval provides access to built-in function calls, such as len and round. 
    The available variable to be used in eval are 'self' and 'cls' both corresponding to the instance and the instance's class respectively.
    """
    
    POSSIBLY_UNSAFE_ENABLE_EVAL = True # Enables the use of pythonic statements instead of only variable names
    _INSTANCES = {}
    
    @classmethod
    def get_instance(cls, _obj):
        obj_id = id(_obj)
        if not obj_id in cls._INSTANCES:
            cls._INSTANCES[obj_id] = cls(_obj)
        cls._INSTANCES[obj_id].update_data()
        return cls._INSTANCES[obj_id]
    
    def __init__(self, _obj):
        self._object = _obj
        self._dict = dict(classname=self._object.__class__.__name__)
        self.update_data()
    
    def __setitem__(self, name, value):
        self._dict[name] = value
    
    def __getitem__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            return self.fallback_getter(name)
    
    def fallback_getter(self, name):
        try:
            getattr(self._object, name)
        except AttributeError:
            if self.__class__.POSSIBLY_UNSAFE_ENABLE_EVAL and name.__contains__('('):
                return eval(name, {'self':self._object, 'cls':self._object.__class__})
            
            curr_obj = self._object
            for name in [attrname for attrname in name.split('.') if len(attrname) > 0]:
                curr_obj = getattr(curr_obj, name)
            return curr_obj
    
    def update_data(self):
        self._dict.update(self._object.__dict__)
