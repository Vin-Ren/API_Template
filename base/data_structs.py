

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


class ReprCustomMapping:
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
    
    def update_data(self):
        self._dict = self._object.__dict__
    
    def __setitem__(self, name, value):
        self._dict[name] = value
    
    def __getitem__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            try:
                getattr(self._object, name)
            except AttributeError:
                curr_obj = self._object
                for name in [attrname for attrname in name.split('.') if len(attrname) > 0]:
                    curr_obj = getattr(curr_obj, name)
                return curr_obj
