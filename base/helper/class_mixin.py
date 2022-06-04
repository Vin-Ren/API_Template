
from ..data_structs import ReprCustomMapping


class ReprMixin:
    _repr_format = "<%(classname)s object>" # Format of __repr__
    
    def __repr__(self):
        return self.__class__._repr_format % ReprCustomMapping.get_instance(self)
