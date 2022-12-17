
from types import NoneType
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from ...helper.decorator import cached
from ...helper.class_mixin import ReprMixin
from .datatypes import *
from .statement import Comparator


class BaseConverter:
    OPTS: Dict[str, str] = {'not_null': 'NOT NULL', 'primary_key':'PRIMARY KEY', 'auto_increment':'AUTO INCREMENT', 'unique':'UNIQUE'}
    TYPE: Dict[type, str] = {int:'INTEGER', str:'TEXT', blob:'BLOB', float:'REAL', datetime:'REAL', bool:'INTEGER', NoneType:'NULL'}
    VALUE: Dict[type, Callable] = {
        int: int, str: str, float:float, 
        blob: str, 
        datetime: lambda dt:dt.timestamp(), 
        bool: lambda _bool:1 if _bool else 0, -1: str}
    REVERSE_VALUE: Dict[type, Callable] = {
        int: int, str:str, float:float, 
        datetime: lambda _s:datetime.fromtimestamp(_s),
        bool: bool, -1: str}


class SQLiteConverter(BaseConverter):
    OPTS: Dict[str, str] = {'not_null': 'NOT NULL', 'primary_key':'PRIMARY KEY', 'auto_increment':'AUTO INCREMENT', 'unique':'UNIQUE'}
    TYPE: Dict[type, str] = {int:'INTEGER', str:'TEXT', blob:'BLOB', float:'REAL', datetime:'REAL', bool:'INTEGER', NoneType:'NULL'}
    VALUE: Dict[type, Callable] = {
        int: int, str: lambda s:str(s) if s is not None else None, float:float, 
        blob: lambda s:str(s) if s is not None else None,
        datetime: lambda dt:(datetime.fromisoformat(dt) if isinstance(dt, str) else datetime.fromtimestamp(dt) if isinstance(dt, (int, float)) else dt).replace(tzinfo=timezone.utc).timestamp(), 
        bool: lambda _bool:1 if _bool else 0, -1: str}
    REVERSE_VALUE: Dict[type, Callable] = {
        int: int, str: lambda s:str(s) if s is not None else None, float:float, 
        blob: lambda s:str(s) if s is not None else None,
        datetime: lambda _i:datetime.utcfromtimestamp(_i),
        bool: bool, -1: str}


class _Field(ReprMixin):
    """SQLite3 Syntax Compliant Field."""
    CONVERTER = SQLiteConverter
    _repr_format = "<%(classname)s '%(name)s' type=%(type.__name__)s>"
    
    def __init__(self, _type: type, name: str = None, *_, default: Any = None, foreign_key: ForeignKey = None, **opts: bool):
        self.type = _type
        self.name = name
        self.opts = {self.__class__.CONVERTER.OPTS.get(name.lower(), name):bool(value) for name, value in opts.items()}
        self.default = default
        self.foreign_key = foreign_key
    
    def make_comparator(self, op, other) -> 'Comparator':
        if self.is_valid(other):
            if self.get_type_str() in ['TEXT', 'BLOB']:
                return Comparator(self.name, op, '"{}"'.format(self.convert_value(other)))
            return Comparator(self.name, op, self.convert_value(other))
    
    def __eq__(self, other) -> 'Comparator':
        return self.make_comparator('==', other)
    
    def __ne__(self, other) -> 'Comparator':
        return Comparator(self.name, '!=', other) # Doesn't need type check and conversion
    
    def __lt__(self, other) -> 'Comparator':
        return self.make_comparator('<', other)
    
    def __le__(self, other) -> 'Comparator':
        return self.make_comparator('<=', other)
    
    def __gt__(self, other) -> 'Comparator':
        return self.make_comparator('>', other)
    
    def __ge__(self, other) -> 'Comparator':
        return self.make_comparator('>=', other)
    
    def is_valid(self, value) -> bool:
        try:
            if self.opts.get('NOT NULL'):
                self.convert_value(value)
            return True
        except:
            return False
    
    def convert_value(self, value):
        return self.CONVERTER.VALUE.get(self.type, self.CONVERTER.VALUE[-1])(value)
    
    def invert_value_conversion(self, value):
        return self.CONVERTER.REVERSE_VALUE.get(self.type, self.CONVERTER.REVERSE_VALUE[-1])(value)
    
    def get_type_str(self) -> str:
        return self.CONVERTER.TYPE.get(self.type)
    
    def get_default_value(self):
        return self.convert_value(self.default) if self.default is not None else None
    
    @property
    def ASC(self) -> tuple:
        "For OrderBy statement"
        return (self.name, 'ASC')

    @property
    def DESC(self) -> tuple:
        "For OrderBy statement"
        return (self.name, 'DESC')

    @cached()
    def generate_field_query(self) -> str:
        type_str = self.get_type_str()
        opts_str = " ".join([opt for opt, enabled in self.opts.items() if enabled and opt not in ['PRIMARY KEY', 'AUTO INCREMENT']]).strip()
        default_str = "DEFAULT {}".format(repr(self.get_default_value())) if self.default is not None else ''
        
        primary_key_str = (""",\nPRIMARY KEY({})""".format('"{}" {}'.format(self.name, "AUTOINCREMENT" if self.opts.get('AUTO INCREMENT', False) else "").strip())) if self.opts.get('PRIMARY KEY', False) else ""
        foreign_key_str = (""",\nFOREIGN KEY({0.key}) REFERENCES "{0.referenced_table}"("{0.referenced_key}")""".format(self.foreign_key)) if self.foreign_key is not None and len(self.foreign_key) >= 3 else ""
        
        # Similiar to => _s = "{name} {type} {settings} {default} {foreign_key}"
        # but dumps extra unnecessary spaces.
        entries = [self.name, type_str, opts_str, default_str]
        sub_strings = [phrase for phrase in entries if phrase.strip()]
        return (" ".join(sub_strings), primary_key_str+foreign_key_str)


class Field(_Field):
    def __init__(self, _type: type, name: str = None, *_, default: Any = None, foreign_key: ForeignKey = None, primary_key: bool = False, not_null: bool = False, auto_increment: bool = False, unique: bool = False, **kwargs):
        super().__init__(_type, name, *_, default=default, foreign_key=foreign_key, primary_key=primary_key, not_null=not_null, auto_increment=auto_increment, unique=unique, **kwargs)
