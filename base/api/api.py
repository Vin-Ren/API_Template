import logging

import requests

from .data_structs import BaseURLCollection, ResponseContainer, Credential, Config
from .parser import ResponseParser
from ..helper.printer import PrettyPrinter
from ..helper.snippets import dict_updater

logger = logging.getLogger(__name__)


class API:
    URLS = BaseURLCollection
    PARSER = ResponseParser
    PRINTER = PrettyPrinter._get_default()
    ALWAYS_CHECK_PREFIXED_BASE_URL = True
    
    _repr_format = "<%(classname)s LoggedIn=%(_logged_in)s>" # Format of __repr__
    _repr_used_properties = [] # used properties in __repr__ formatting, if no properties are used, leave this empty.
    
    def __init__(self, credentials: Credential, config: Config, initialize=True, **kw):
        self.credentials = credentials
        self.config = config
        
        self.recent_responses = ResponseContainer()
        self.recent_method_response = dict.fromkeys(['request'])
        self.session = requests.Session()
        
        self._logged_in = False

        if initialize:
            self._init(**kw)
    
    @property
    def headers(self):
        """Shorthand for api.session.headers"""
        return self.session.headers

    @property
    def cookies(self):
        """Shorthand for api.session.cookies"""
        return self.session.cookies
    
    def __repr__(self):
        mapping = dict_updater(self.__dict__, {name:getattr(self, name) for name in self.__class__._repr_used_properties})
        return self.__class__._repr_format % dict(classname=self.__class__.__name__, **mapping)

    def _init(self):
        """Where you can set up the session, login, initialize directories, load cookies, etc. by default, this will set _logged_in value as login method return value."""
        self._logged_in = bool(self.login())
    
    def login(self):
        """Where you can do your login process. By default returns True. Should only return booleans."""
        return True

    def request_params_preprocessor(self, params):
        """Modify request params before request. Could be useful if you need to add stuff like apiKey."""
        return params

    def _request(self, method: str, url: str, *, params: dict = {}, **kw):
        """Similiar to api.request, but without putting the response somewhere and print_debug."""
        if self.ALWAYS_CHECK_PREFIXED_BASE_URL:
            BASE_URL = self.URLS.BASE
            url = url if url.startswith(BASE_URL) else BASE_URL+(url if url.startswith('/') else '/{}'.format(url))
        response = self.session.request(method=method.upper(), url=url, params=self.request_params_preprocessor(params), **kw)
        return response

    def request(self, method: str, url: str, *args, params: dict = {}, **kw):
        """Layer of abstraction for requests to go through. create a request, and put it into recent_reponses and recent_method_response, then it would call PRINTER's print_debug method."""
        resp = self._request(method, url, *args, params=params, **kw)
        self.recent_responses.append(resp)
        self.recent_method_response['request'] = resp
        
        self.PRINTER.print_debug('Request Process', 
                                {'Method':method, 'Url':url, 'Params': params, 'Status Code': resp.status_code})
        return resp
    
    
    def _get(self, *args, **kwargs):
        "Shorthand for api._request with method=GET"
        return self._request('GET', *args, **kwargs)
    
    def _post(self, *args, **kwargs):
        "Shorthand for api._request with method=POST"
        return self._request('POST', *args, **kwargs)
    
    def _put(self, *args, **kwargs):
        "Shorthand for api._request with method=PUT"
        return self._request('PUT', *args, **kwargs)
    
    def _patch(self, *args, **kwargs):
        "Shorthand for api._request with method=PATCH"
        return self._request('PATCH', *args, **kwargs)
    
    def _delete(self, *args, **kwargs):
        "Shorthand for api._request with method=DELETE"
        return self._request('DELETE', *args, **kwargs)
    
    
    def get(self, *args, **kwargs):
        "Shorthand for api.request with method=GET"
        return self.request('GET', *args, **kwargs)
    
    def post(self, *args, **kwargs):
        "Shorthand for api.request with method=POST"
        return self.request('POST', *args, **kwargs)
    
    def put(self, *args, **kwargs):
        "Shorthand for api.request with method=PUT"
        return self.request('PUT', *args, **kwargs)
    
    def patch(self, *args, **kwargs):
        "Shorthand for api.request with method=PATCH"
        return self.request('PATCH', *args, **kwargs)
    
    def delete(self, *args, **kwargs):
        "Shorthand for api.request with method=DELETE"
        return self.request('DELETE', *args, **kwargs)