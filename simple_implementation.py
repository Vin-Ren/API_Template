from enum import Enum

from base.api.api import API
from base.api.data_structs import BaseURLCollection, Credential, Config, RegexCollection, BaseAPIObject
from base.api.parser import RegexParser
from base.helper.decorator import convert_to


class UrlCollection(BaseURLCollection):
    BASE = "https://osu.ppy.sh"
    BASE_API = BASE+"/api"
    
    home = BASE
    session = "%s/session" % BASE
    formattable_beatmapset = "%s/beatmapsets/{0[beatmapset_id]}" % BASE
    formattable_beatmapset_download = "%s/download" % formattable_beatmapset
    
    get_beatmaps = "%s/get_beatmaps" % BASE_API
    get_user = "%s/get_user" % BASE_API


class BaseOsuObject(BaseAPIObject):
    pass

class ApprovedEnum(Enum):
    Loved = 4
    Qualified = 3
    Approved = 2
    Ranked = 1
    Pending = 0
    WIP = -1
    Graveyard = -2

class Beatmap(BaseOsuObject):
    REQUIRED_FIELDS = ['beatmap_id', 'beatmapset_id', 'approved', 'title', 'version']
    def __repr__(self):
        return "<{} object id={} beatmapset_id={} approved={} version={}>".format(self.__class__.__name__, self.beatmap_id, self.beatmapset_id, ApprovedEnum(int(self.approved)).name, self.version)
    def __str__(self):
        return "{0[beatmapset_id]} {0[artist]} - {0[title]} ({0[version]})".format(self)

class User(BaseOsuObject):
    REQUIRED_FIELDS = ['user_id', 'username', 'join_date', 'level', 'pp_raw']
    def __repr__(self):
        return "<{} object id={} username={} level={} pp={}>".format(self.__class__.__name__, self.user_id, self.username, round(float(self.level)), round(float(self.pp_raw)))
    def __str__(self):
        return "User#{0[user_id]} {0[username]}".format(self)


class OsuAPI(API):
    URLS = UrlCollection
    PARSER = RegexParser(RegexCollection)
    
    _repr_format = "<%(classname)s LoggedIn=%(_logged_in)s Username=%(username)s>"
    
    def __init__(self, api_key: str, credentials: Credential, config: Config, initialize=True, **kw):
        super().__init__(credentials, config, initialize=False, **kw)
        self.api_key = api_key
        self.recent_method_response = dict.fromkeys(['request', 'get_csrf_token', 'login'])
        
        if initialize:
            self._init(**kw)
    
    @property
    def username(self):
        return self.credentials.username
    
    def _init(self):
        self.headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'}
        return super()._init()
    
    def request_params_preprocessor(self, params):
        params.update({'k': self.api_key})
        return params
    
    def get_csrf_token(self):
        resp = self.get(self.URLS.home)
        self.recent_method_response['get_csrf_token'] = resp
        if resp.status_code == 200:
            match_dict = self.PARSER.parse_one_csrf_token(resp.text)
            try:
                return match_dict.get('csrftoken')
            except AttributeError:
                print("CSRF Token Error: Could not find CSRF token in the page.")
        elif resp.status_code == 429:
            print("CSRF Token Error: 429 Too Many Requests.")
    
    def login(self):
        data = dict(self.credentials)
        data['_token'] = self.get_csrf_token()
        headers = {'referer': self.URLS.home}
        
        resp = self.session.post(self.URLS.session, data=data, headers=headers)
        self.recent_method_response['login'] = resp
        
        self.PRINTER.print_debug('Login Process', 
                                {'Data': data, 'Headers': headers, 'Status Code': resp.status_code})
        return resp.ok
    
    @convert_to(Beatmap, iterable=True)
    def get_beatmaps(self, params: dict):
        return self.get(url=self.URLS.get_beatmaps, params=params)
    
    @convert_to(User, iterable=True)
    def get_users(self, params: dict):
        return self.get(url=self.URLS.get_user, params=params)
