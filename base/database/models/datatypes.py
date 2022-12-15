
from collections import namedtuple
from datetime import datetime


ForeignKey = namedtuple('ForeignKey', ('key', 'referenced_table', 'referenced_key'))
BLOB = blob = type('BLOB', (), {})
INT = Int = int
STR = Str = str
FLOAT = Float = float
DATETIME = DateTime = datetime
BOOLEAN = Boolean = bool

__all__ = ['ForeignKey', 
           'BLOB', 'blob', 
           'INT', 'Int', 
           'STR', 'Str', 
           'Float', 'Float', 
           'DATETIME', 'DateTime', 'datetime', 
           'BOOLEAN', 'Boolean']
