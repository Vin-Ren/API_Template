

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
