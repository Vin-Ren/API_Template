import re

from ..data_structs import *
from ..database.models import Model
from ..helper.snippets import dict_updater


class BaseURLCollection:
    BASE = "https://"


class RegexCollection:
    CSRF_TOKEN = re.compile(r".*?csrf-token.*?content=\"(?P<csrftoken>.*?)\">", re.DOTALL)


class ResponseContainer(list):
    """Wrapper for a list, with first and last property added."""
    @property
    def first(self):
        return self[0] if len(self) >= 1 else None
    
    @property
    def last(self):
        return self[-1] if len(self) >= 1 else None


class BaseAPIObject(ObjectifiedDict, Model):
    """
    A Base to inherit from for API Objects. Inherits from both ObjectifiedDict and Model."""
    REQUIRED_FIELDS = []
    DEFAULT_VALUES = {}
    
    def __init__(self, _dict={}, *_, **kwargs):
        _dict.update(kwargs)
        super().__init__(_dict)
        for key, value in self.__class__.DEFAULT_VALUES.items():
            if key in self and self[key] is not None:
                continue
            self[key] = value
    
    @property
    def valid(self):
        return all(map(lambda key:self.__contains__(key), self.REQUIRED_FIELDS))
