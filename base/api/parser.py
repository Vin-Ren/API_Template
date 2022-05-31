import abc

import requests


class ResponseParser(abc.ABC):
    @abc.abstractmethod
    def parse(self):
        pass


class RegexResponseParser(ResponseParser):
    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            if name.startswith('parse_one_'):
                return (lambda *args, **kwargs: self.parse_one(name.split('parse_one_', 1)[-1].upper(), *args, **kwargs))
            if name.startswith('parse_'):
                return (lambda *args, **kwargs: self.parse(name.split('parse_', 1)[-1].upper(), *args, **kwargs))
    
    def __init__(self, regex_collection: type):
        self.regex_collection = regex_collection
    
    def parse(self, regex_name: str, string: str):
        regex = getattr(self.regex_collection, regex_name)
        for match in regex.finditer(string):
            yield match.groupdict()
    
    def parse_one(self, regex_name: str, string: str):
        regex = getattr(self.regex_collection, regex_name)
        match = regex.search(string)
        return match.groupdict() if match is not None else None
    
    def parse_response(self, regex_name: str, response: requests.Response):
        return self.parse(regex_name, string=response.text)
    
    def parse_one_from_response(self, regex_name: str, response: requests.Response):
        return self.parse_one(regex_name, response.text)
