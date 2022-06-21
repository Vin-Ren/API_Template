
import sqlite3
from typing import List, Union

from base.database.models.base import Model, ModelMeta
from ..helper.class_mixin import ReprMixin

from .cursor import CursorProxy


class BaseManager(ReprMixin):
    TABLES = []
    _repr_format = "<%(classname)s DB Manager>"
    
    def __init__(self, database:str, *, initialize=True):
        self.database=database
        
        if initialize:
            self._init()
    
    def _init(self):
        pass


class SQLiteDB(BaseManager):
    TABLES = []
    
    _repr_format = "<%(classname)s Manager>"
    
    def __init__(self, database: str, *, initialize=True):
        self.database = database
        self.connection = sqlite3.connect(database=self.database)
        self.connection.row_factory = self.row_factory
        self.cursor = self.connection.cursor()
        
        if initialize:
            self._init()
    
    @staticmethod
    def row_factory(cursor, row):
        return {col[0]:row[i] for i, col in enumerate(cursor.description)}
    
    def execute(self, *args, **kwargs):
        return self.cursor.execute(*args, **kwargs)
    
    def executemany(self, *args, **kwargs):
        return self.cursor.executemany(*args, **kwargs)
    
    def commit(self):
        return self.connection.commit()
    
    def _init(self):
        for table in self.__class__.TABLES:
            self.create_table(table)
    
    def create_table(self, model: Union[ModelMeta, Model]):
        self.cursor.execute(model.make_create_query())
        self.connection.commit()
    
    def create_model(self, model):
        """Alias for craete_table"""
        self.create_table(model)
    
    def insert(self, obj: Model, **insertKwargs):
        self.cursor.execute(*obj.make_insert_args(**insertKwargs))
        self.connection.commit()
    
    def insert_many(self, obj_list: List[Model], **insertKwargs):
        """Uses executemany and can insert many objects of different models."""
        
        model_groups = {}
        for obj in obj_list:
            model_groups[obj.__class__] = model_groups.get(obj.__class__, []) + [obj]
        
        query_groups = {table.make_insert_query(**insertKwargs) : [obj.make_insert_values() for obj in objs] for table, objs in model_groups.items()}

        for query_string, execute_many_values in query_groups.items():
            self.cursor.executemany(query_string, execute_many_values)
            self.connection.commit() # Commit for every model group.


class MultiThreadedSQLiteDB(SQLiteDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cursor = self.cursor
        self.cursor: CursorProxy = CursorProxy(self.database, self._cursor)
