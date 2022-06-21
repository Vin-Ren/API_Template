import logging

import requests

from base.helper.decorator import timed_cache


from ..data_structs import Credential, Config
from .data_structs import BaseURLCollection, ResponseContainer
from .parser import Parser
from ..helper.class_mixin import ReprMixin, PluggableMixin
from ..plugins.download_manager import DownloadManager
from ..plugins.cookies_manager import CookiesManager
from ..helper.printer import PrettyPrinter


logger = logging.getLogger(__name__)


class API(ReprMixin, PluggableMixin):
    URLS = BaseURLCollection
    PARSER = Parser
    PRINTER = PrettyPrinter._get_default()
    ALWAYS_CHECK_PREFIXED_BASE_URL = True
    LOGGED_IN_CACHE_LIFESPAN = 15*60
    
    PLUGINS = []
    
    _repr_format = "<%(classname)s LoggedIn=%(logged_in)s>" # Format of __repr__
    
    def __init_subclass__(cls):
        if not hasattr(cls.check_logged_in, '_cache_lifespan'):
            cls.check_logged_in = timed_cache(cls.LOGGED_IN_CACHE_LIFESPAN)(cls.check_logged_in)
        cls.check_logged_in._cache_lifespan = cls.LOGGED_IN_CACHE_LIFESPAN
        return super().__init_subclass__()
    
    def __init__(self, credentials: Credential, config: Config, initialize=True, **kw):
        super().__init__()
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
    
    @headers.setter
    def headers(self, replacer):
        self.session.headers = replacer
    
    @cookies.setter
    def cookies(self, replacer):
        self.session.cookies = replacer

    def _init(self):
        """Where you can set up the session, login, initialize directories, load cookies, etc. by default, this will set _logged_in value as login method return value."""
        self._logged_in = bool(self.login())
    
    def login(self):
        """Where you can do your login process. By default returns True. Should only return booleans which represents the result of the login action."""
        return True

    @timed_cache(LOGGED_IN_CACHE_LIFESPAN)
    def check_logged_in(self):
        """Should be overriden with logic to check whether the user is logged in or not. This method would automatically be decorated with timed_cache decorator and with lifespan as the class' LOGGED_IN_CACHE_LIFESPAN attribute."""
        return self._logged_in

    @property
    def logged_in(self):
        return self.check_logged_in()

    def request_params_preprocessor(self, params):
        """Modify request params before request. Could be useful if you need to add stuff like apiKey. This is applied to all requests passed through _request and request method."""
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
        
        logger.debug("Request Process: Method=%s Url=%s Params=%s StatusCode=%s" % (method, url, params, resp.status_code))
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
