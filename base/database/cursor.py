from collections import namedtuple
from queue import Queue
import sqlite3
from threading import Thread

from typing import Any, Dict, Tuple


CursorTask = namedtuple('CursorTask', ['target_method', 'args', 'kwargs'])


class CursorProxy:
    def __init__(self, database: str, cursor: sqlite3.Cursor = None, initialize = True):
        self.database = database
        self.connection: sqlite3.Connection = None
        self.cursor: sqlite3.Cursor = cursor
        
        self.proxy_connection: sqlite3.Connection = None
        self.proxy_cursor: sqlite3.Cursor = None
        self.daemon: Thread = Thread(target=self.process_queued_tasks, name='CursorProxy Daemon Thread', daemon=True)
        self.queue: Queue = Queue()
        
        self._proxy_map = {}
        
        if cursor is not None:
            self.connection = self.cursor.connection
        else:
            self.connection = sqlite3.connect(self.database)
            self.cursor = self.connection.cursor()
        
        if initialize:
            self._init()
    
    def _init(self):
        self.daemon.start()
    
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self._proxy_map.get(name, self.make_proxy(name))
    
    def __call__(self, *args, **kwds):
        return self.cursor.__call__(*args, **kwds)
    
    def __repr__(self):
        return "<{} object for database={}>".format(self.__class__.__name__, self.database)
    
    def process_queued_tasks(self):
        try:
            self.proxy_connection = sqlite3.connect(self.database)
            self.proxy_cursor = self.proxy_connection.cursor()
            while True:
                task: CursorTask = self.queue.get(True)
                method = self.proxy_cursor
                for accessor in task.target_method.split('.'):
                    method = method.__getattribute__(accessor)
                method(*task.args, **task.kwargs)
        finally:
            self.proxy_cursor.close()
    
    def enqueue_task(self, method_name: str, args: Tuple, kwargs: Dict, return_value: bool = False):
        return self.queue.put(CursorTask(method_name, args, kwargs))
    
    def make_proxy(self, method_name: str):
        if not hasattr(self.proxy_cursor, method_name):
            raise AttributeError('\'{}\' is not found in this cursor object.'.format(method_name))
        def _proxy(*args, **kwargs):
            return self.proxy(method_name, *args, **kwargs)
        return _proxy

    def proxy(self, method_name: str, *args, immediate: bool = False, **kwargs):
        if immediate:
            return self.cursor.__getattribute__(method_name)(*args, **kwargs)
        return self.enqueue_task(method_name, args=args, kwargs=kwargs)

    def commit_proxy(self):
        return self.proxy('connection.commit')
