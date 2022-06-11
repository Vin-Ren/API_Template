import re

from ..data_structs import *


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


class BaseAPIObject(ObjectifiedDict):
    REQUIRED_FIELDS = []
    @property
    def valid(self):
        return all(map(lambda key:self.__contains__(key), self.REQUIRED_FIELDS))
