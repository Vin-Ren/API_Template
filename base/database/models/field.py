
from types import NoneType
from datetime import datetime
from typing import Any, Dict, Literal

from ...helper.decorator import cached
from ...helper.class_mixin import ReprMixin
from .datatypes import *


class BaseConverter:
    OPTS = {'not_null': 'NOT NULL', 'primary_key':'PRIMARY KEY', 'auto_increment':'AUTO INCREMENT', 'unique':'UNIQUE'}
    TYPE = {int:'INTEGER', str:'TEXT', blob:'BLOB', float:'REAL', datetime:'TEXT', bool:'INTEGER', NoneType:'NULL'}
    VALUE = {int: int, str: str, float:float, 
            datetime: lambda dt:dt.isoformat(), 
            bool: lambda _bool:1 if _bool else 0, -1: str}
    REVERSE_VALUE = {int: int, str:str, float:float, 
                    datetime: lambda _s:datetime.fromisoformat(_s),
                    bool: bool, -1: str}


class SQLiteConverter(BaseConverter):
    OPTS = {'not_null': 'NOT NULL', 'primary_key':'PRIMARY KEY', 'auto_increment':'AUTO INCREMENT', 'unique':'UNIQUE'}
    TYPE = {int:'INTEGER', str:'TEXT', blob:'BLOB', float:'REAL', datetime:'TEXT', bool:'INTEGER', NoneType:'NULL'}
    VALUE = {int: int, str: str, float:float, 
            datetime: lambda dt:datetime.fromisoformat(dt).isoformat() if isinstance(dt, str) else datetime.fromtimestamp(dt).isoformat() if isinstance(dt, int) else dt.isoformat(), 
            bool: lambda _bool:1 if _bool else 0, -1: str}
    REVERSE_VALUE = {int: int, str:str, float:float, 
                    datetime: lambda _s:datetime.fromisoformat(_s),
                    bool: bool, -1: str}


class Field(ReprMixin):
    """SQLite3 Syntax Compliant Field."""
    CONVERTER = SQLiteConverter
    _repr_format = "<%(classname)s '%(name)s' type=%(type.__name__)s>"
    
    def __init__(self, _type: type, name: str = None, *_, default: Any = None, foreign_key: ForeignKey = None, **opts: Dict[Literal['not_null', 'primary_key', 'auto_increment', 'unique'], bool]):
        self.type = _type
        self.name = name
        self.opts = {self.__class__.CONVERTER.OPTS.get(name.lower(), name):bool(value) for name, value in opts.items()}
        self.default=default
        self.foreign_key = foreign_key
    
    def is_valid(self, value):
        try:
            if self.opts.get('NOT NULL'):
                self.convert_value(value)
            return True
        except:
            raise
    
    def convert_value(self, value):
        return self.CONVERTER.VALUE.get(self.type, self.CONVERTER.VALUE[-1])(value)
    
    def invert_value_conversion(self, value):
        return self.CONVERTER.REVERSE_VALUE.get(self.type, self.CONVERTER.REVERSE_VALUE[-1])(value)
    
    def get_type_str(self):
        return self.CONVERTER.TYPE.get(self.type)
    
    def get_default_value(self):
        return self.convert_value(self.default) if self.default is not None else None
    
    @cached()
    def generate_field_query(self):
        type_str = self.get_type_str()
        opts_str = " ".join([opt for opt, enabled in self.opts.items() if enabled])
        default_str = "DEFAULT {}".format(self.get_default_value()) if self.default is not None else ''
        
        foreign_key_str = (""",\nFOREIGN KEY({0.key}) REFERENCES "{0.referenced_table}"("{0.referenced_key}")""".format(self.foreign_key)) if self.foreign_key is not None and len(self.foreign_key) >= 3 else ""
        
        # Similiar to => _s = "{name} {type} {settings} {default} {foreign_key}"
        # but dumps extra unnecessary spaces.
        entries = [self.name, type_str, opts_str, default_str]
        sub_strings = [phrase for phrase in entries if phrase.strip()]
        return (" ".join(sub_strings), foreign_key_str)

