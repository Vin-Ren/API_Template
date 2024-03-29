import abc

import requests
import bs4


class Parser(abc.ABC):
    """Base parser, essentially empty, you can use presets available, modify them or even create one specific to your own project."""


class RegexParser(Parser):
    def __getattribute__(self, name: str):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.dynamic_parse(name)
    
    def dynamic_parse(self, name):
        if name.startswith('parse_one_'):
            regex_name = name.split('parse_one_', 1)[-1].upper()
            text_parser, response_parser = self.parse_one, self.parse_one_from_response
        elif name.startswith('parse_'):
            regex_name = name.split('parse_', 1)[-1].upper()
            text_parser, response_parser = self.parse, self.parse_response
        else:
            raise AttributeError("Regex Response Parser has no attribute with name={}".format(name))
        
        if not hasattr(self.regex_collection, regex_name):
            raise AttributeError("Regex with name={} is not found.".format(regex_name))
        
        return (lambda source, *args, **kwargs: 
                    text_parser(regex_name, source, *args, **kwargs)
                    if isinstance(source, str) else 
                    response_parser(regex_name, source, *args, **kwargs))
    
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


class BSParser(Parser):
    """Base BeautifulSoup Parser, really empty. You should extend this class with your own subclass to accomodate your need."""
    def __init__(self, parser: str = 'html.parser'):
        self.parser=parser

    def get_soup(self, text: str):
        return bs4.BeautifulSoup(text, self.parser)
        
    def get_soup_from_response(self, resp:requests.Response):
        return self.get_soup(resp.text)
