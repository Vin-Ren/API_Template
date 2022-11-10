
from .base import BasePlugin, PluggableMixin

from .cookies_manager import CookiesCachingMethod, CookiesManager
from .download_manager import DownloadFileHandler, DownloadManager

CookiesMan=CookiesManager
DownloadMan=DownloadManager
