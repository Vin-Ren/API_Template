from base.api import API
import requests
import bs4
from base.plugins.cookies_manager import CookiesCachingMethod
from base.helper.printer import PrettyPrinter
from base import api as _api, helper, plugins, database, data_structs


def sandboxify(api:API):
    """Pass in an API object to get a basic dictionary containing some useful bits to simulate stuff."""
    return {'basic_config':api.get_basic_config(), 'plugins':api.PLUGINS, 'parser':api.PARSER, 'urls':api.URLS, 'session':api.session, # from the api object
            'api':_api, 'helper':helper, 'plugins':plugins, 'database':database, 'data_structs':data_structs, # from template
            'CookiesCachingMethod':CookiesCachingMethod, 'Printer':PrettyPrinter, # from template
            'requests':requests, 'bs4':bs4 # external libs
            }
