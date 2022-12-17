from queue import Queue
import sqlite3
from threading import Thread
from typing import Dict, Tuple


class CursorTask:
    """A CursorTask object, using Queue to block until result is available"""
    def __init__(self, target_method, args, kwargs):
        self.target_method = target_method
        self.args = args
        self.kwargs = kwargs
        self.result_q = Queue()
        self.done = False
    
    def get_result(self, block=True, timeout=None):
        """Calls result_q.get"""
        if self.done:
            return
        rv = self.result_q.get(block=block, timeout=timeout)
        self.done = True
        return rv


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
            self.proxy_connection.row_factory = self.connection.row_factory
            self.proxy_cursor = self.proxy_connection.cursor()
            while True:
                try:
                    task: CursorTask = self.queue.get(True)
                    res = None
                    if task.target_method.__contains__('.'):
                        method = self.proxy_cursor
                        for accessor in task.target_method.split('.'):
                            method = method.__getattribute__(accessor)
                        res = method(*task.args, **task.kwargs)
                    else:
                        res = self.proxy_cursor.__getattribute__(task.target_method)(*task.args, **task.kwargs)
                    task.result_q.put(res)
                except Exception as exc:
                    continue
        finally:
            self.proxy_cursor.close()
    
    def enqueue_task(self, method_name: str, args: Tuple, kwargs: Dict, return_value: bool = False):
        task = CursorTask(method_name, args, kwargs)
        self.queue.put(task)
        return task
    
    def make_proxy(self, method_name: str):
        if not hasattr(self.proxy_cursor, method_name):
            raise AttributeError('\'{}\' is not found in this cursor object.'.format(method_name))
        def _proxy(*args, **kwargs):
            return self.proxy(method_name, *args, **kwargs)
        return _proxy

    def proxy(self, method_name: str, *args, block: bool = False, **kwargs):
        task = self.enqueue_task(method_name, args=args, kwargs=kwargs)
        if not block:
            return task
        return task.get_result(block=True)

    def commit_proxy(self):
        return self.proxy('connection.commit')
    
    def fetchone(self, *args, **kwargs):
        return self.proxy('fetchone', *args, *kwargs, block=True)
    
    def fetchmany(self, *args, **kwargs):
        return self.proxy('fetchmany', *args, *kwargs, block=True)
    
    def fetchall(self, *args, **kwargs):
        return self.proxy('fetchall', *args, *kwargs, block=True)
