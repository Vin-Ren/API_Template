import json
import pickle
from enum import Enum

import requests.utils

from .base import BasePlugin


class CookiesCachingMethod(Enum):
    def getExtension(self):
        return self.value.lower()
    SIMPLE_JSON = 'SIMPLE.JSON'
    JSON = 'JSON'
    PICKLE = 'PICKLE'
    STRING = 'STRING'
    TXT = 'TXT'
    TEXT = 'TEXT'


class CookiesManager(BasePlugin):
    DEFAULT_COOKIES_CACHING_METHOD = CookiesCachingMethod.JSON
    _repr_format = "<%(classname)s DEFAULT_COOKIES_CACHING_METHOD=%(DEFAULT_COOKIES_CACHING_METHOD)s>" # Format of __repr__
    
    REQUIRED_CONFIGS = dict(cookies_caching_method=DEFAULT_COOKIES_CACHING_METHOD, 
                            cached_cookies_filename='.cached', 
                            data_passthrough={})
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __cookies_resolve_filename(self, method, filename=None):
        method = CookiesCachingMethod(method if method is not None else self.config.cookies_caching_method)
        filename = self.config.cached_cookies_filename if filename is None else filename
        filename = filename+'.'+method.getExtension() if not filename.lower().__contains__(method.getExtension().lower()) else filename
        return filename
    
    def load_cookies_from_string(self, cookies_string):
        cookies_entries = [entry.strip().split('=', 1) for entry in cookies_string.split(";")]
        cookies = requests.utils.cookiejar_from_dict({k:v for k,v in cookies_entries})
        self.api.session.cookies.update(cookies)
    
    def load_cookies(self, method=None, filename=None):
        filename = self.__cookies_resolve_filename(method=method, filename=filename)
        
        if method == CookiesCachingMethod.JSON:
            with open(filename, 'r') as f:
                for entry in json.load(f):
                    self.session.cookies.set(**entry)
        
        elif method == CookiesCachingMethod.SIMPLE_JSON:
            with open(filename, 'r') as f:
                cookies = requests.utils.cookiejar_from_dict(json.load(f))
                self.session.cookies.update(cookies)
        
        elif method in [CookiesCachingMethod.TEXT, CookiesCachingMethod.TXT]:
            with open(filename, 'r') as f:
                self.load_cookies_from_string(f.read())
        
        elif method == CookiesCachingMethod.STRING:
            self.load_cookies_from_string(self.config.data_passthrough.get('cookies_string',''))
        
        elif method == CookiesCachingMethod.PICKLE:
            with open(filename, 'rb') as f:
                self.session.cookies.update(pickle.load(f))
    
    def dump_cookies(self, method=None, filename=None):
        filename = self.__cookies_resolve_filename(method=method, filename=filename)
        
        if method == CookiesCachingMethod.JSON:
            cookie_attrs = ["version", "name", "value", "port", "domain", "path", "secure",
                            "expires", "discard", "comment", "comment_url", "rfc2109"]
            with open(filename, 'w') as f:
                json.dump([{attr: getattr(cookie, attr) for attr in cookie_attrs} for cookie in self.session.cookies], f, indent=4)
        
        elif method == CookiesCachingMethod.SIMPLE_JSON:
            with open(filename, 'w') as f:
                json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)
        
        elif method in [CookiesCachingMethod.TEXT, CookiesCachingMethod.TXT]:
            with open(filename, 'w') as f:
                cookies_entries = requests.utils.dict_from_cookiejar(self.session.cookies)
                f.write("; ".join(["{}={}".format(k,v) for k,v in cookies_entries.items()]))
        
        elif method == CookiesCachingMethod.PICKLE:
            with open(filename, 'wb') as f:
                pickle.dump(self.session.cookies, f, pickle.HIGHEST_PROTOCOL)
