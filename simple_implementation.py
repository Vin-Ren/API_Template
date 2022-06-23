from enum import Enum

from datetime import datetime

from base.api.api import API
from base.api.data_structs import BaseURLCollection, Credential, Config, RegexCollection, BaseAPIObject
from base.api.parser import RegexParser
from base.database.models.field import Field
from base.helper.decorator import convert_to, check_attrs, exception_handler
from base.plugins.cookies_manager import CookiesManager
from base.plugins.download_manager import DownloadManager
from base.database.manager import MultiThreadedSQLiteDB


class UrlCollection(BaseURLCollection):
    BASE = "https://osu.ppy.sh"
    BASE_API = BASE+"/api"
    
    home = BASE
    session = "%s/session" % BASE
    formattable_beatmapset = "%s/beatmapsets/{0[beatmapset_id]}" % BASE
    formattable_beatmapset_download = "%s/download" % formattable_beatmapset
    
    get_beatmaps = "%s/get_beatmaps" % BASE_API
    get_user = "%s/get_user" % BASE_API


class ApprovedEnum(Enum):
    Loved = 4
    Qualified = 3
    Approved = 2
    Ranked = 1
    Pending = 0
    WIP = -1
    Graveyard = -2


class BaseOsuObject(BaseAPIObject):
    pass


class Beatmap(BaseOsuObject):
    __TABLE_NAME__ = 'beatmaps'
    REQUIRED_FIELDS = ['beatmap_id', 'beatmapset_id', 'approved', 'title', 'version']
    # First type of implementation for Model
    beatmap_id = Field(int, primary_key=True, not_null=True, unique=True)
    beatmapset_id = Field(int, not_null=True)
    approved = Field(int, not_null=True)
    title = Field(str, not_null=True)
    version = Field(str, not_null=True)
    
    def __repr__(self):
        if not self.valid:
            return "<Invalid {} object>".format(self.__class__.__name__)
        return "<{} object id={} beatmapset_id={} approved={} version={}>".format(self.__class__.__name__, self.beatmap_id, self.beatmapset_id, ApprovedEnum(int(self.approved)).name, self.version)
    def __str__(self):
        return "{0[beatmapset_id]} {0[artist]} - {0[title]} ({0[version]})".format(self)


class User(BaseOsuObject):
    __TABLE_NAME__ = 'users'
    REQUIRED_FIELDS = ['user_id', 'username', 'join_date', 'level', 'pp_raw']
    # Second type of implementation for Model
    __FIELDS__ = [
        Field(int, 'user_id', primary_key=True, not_null=True, unique=True), 
        Field(str, 'username', not_null=True, unique=True),
        Field(datetime, 'join_date', not_null=True),
        Field(float, 'level', not_null=True),
        Field(float, 'pp_raw', not_null=True)]

    def __repr__(self):
        if not self.valid:
            return "<Invalid {} object>".format(self.__class__.__name__)
        return "<{} object id={} username={} level={} pp={}>".format(self.__class__.__name__, self.user_id, self.username, round(float(self.level)), round(float(self.pp_raw)))
    def __str__(self):
        return "User#{0[user_id]} {0[username]}".format(self)


class OsuDB(MultiThreadedSQLiteDB):
    TABLES = [Beatmap, User]


class BaseOsuException(BaseException):
    pass


class NotLoggedIn(BaseOsuException, RuntimeError):
    pass


@exception_handler # Naming conflict if referenced again, but will you?
def exception_handler(exception):
    if isinstance(exception, NotLoggedIn):
        print("This functionality requires you to be logged in.")
    else:
        raise exception


class OsuAPI(API):
    URLS = UrlCollection
    PARSER = RegexParser(RegexCollection)
    
    PLUGINS = [DownloadManager, CookiesManager]
    REQUIRED_CONFIGS = {'database': 'db.sqlite3'}
    
    _repr_format = "<%(classname)s LoggedIn=%(logged_in)s Username=%(username)s>"
    
    def __init__(self, api_key: str, credentials: Credential, config: Config, initialize=True, **kw):
        super().__init__(credentials, config, initialize=False, **kw)
        self.api_key = api_key
        self.db = OsuDB(config.database)
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
    def get_beatmaps(self, params: dict = {}):
        return self.get(url=self.URLS.get_beatmaps, params=params)
    
    @convert_to(User, iterable=True)
    def get_users(self, params: dict = {}):
        return self.get(url=self.URLS.get_user, params=params)
    
    def import_beatmaps_to_db(self, params: dict = {}):
        return self.db.insert_many(self.get_beatmaps(params=params))
    
    def import_users_to_db(self, params: dict = {}):
        return self.db.insert_many(self.get_users(params=params))
    
    @exception_handler
    @check_attrs(logged_in=True)
    def download_beatmap(self, filename, beatmap, params={}):
        beatmapset_url = self.URLS.formattable_beatmapset.format(beatmap)
        beatmapset_download_url = self.URLS.formattable_beatmapset_download.format(beatmap)
        headers = {'referer': beatmapset_url}
        
        downloader: DownloadManager = self[DownloadManager] # Only for type hinting
        progress_info = downloader.download_to_file(filename, url=beatmapset_download_url, params=params, headers=headers, allow_redirects=True)
        
        self.PRINTER.print_debug('Download Process', 
                                {'Beatmap Info':beatmap, 'Download Url':beatmapset_download_url, 
                                 'Beatmapset Url': beatmapset_url, 'Target File Stream': repr(progress_info.pipe_handler), 
                                 'Params': params, 'Status Code': progress_info.stream.status_code})
        return bool(progress_info)


def get_api():
    api_key = input('API KEY:')
    credentials = Credential(username=input('USERNAME:'), password=input('PASSWORD:'))
    basic_config = OsuAPI.get_basic_config()
    return OsuAPI(api_key, credentials, basic_config)


if __name__ == '__main__':
    pass
