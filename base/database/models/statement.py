import abc
from types import NoneType
from typing import List, Tuple, Literal, Union


# Base Classes

class Statement(abc.ABC):
    @abc.abstractmethod
    def make_query(self):
        pass
    
    def __repr__(self) -> str:
        return "<Statement>"
    
    def __str__(self) -> str:
        return self.make_query()
    
    def __and__(self, other) -> 'Statement':
        return AND(self, other)
    
    def __or__(self, other) -> 'Statement':
        return OR(self, other)


class BaseComparator(Statement):
    pass

class BaseOperator(Statement):
    pass


class UnaryOperator(BaseOperator):
    OPERATOR = ''
    def __init__(self, statement: Statement):
        self.statement = statement
    
    def make_query(self) -> str:
        return '{} {}'.format(self.__class__.OPERATOR, self.statement)


class BinaryOperator(BaseOperator):
    OPERATOR = ''
    def __init__(self, left: Statement, right: Statement):
        self.left = left
        self.right = right
    
    def make_query(self) -> str:
        return '{} {} {}'.format(self.left.make_query(), self.__class__.OPERATOR, self.right.make_query())


class JoinOperator(BinaryOperator):
    "Similiar to BinaryOperator, but with no limit for statements"
    OPERATOR = ''
    def __init__(self, *statements: Statement):
        self.statements = statements
    
    def make_query(self) -> str:
        return ' {} '.format(self.__class__.OPERATOR).join([statement.make_query() for statement in self.statements])


# Operators

class NOT(UnaryOperator):
    OPERATOR = 'NOT'

class OR(JoinOperator):
    OPERATOR = 'OR'

class AND(JoinOperator):
    OPERATOR = 'AND'


#Comparator

class Comparator(BaseComparator):
    def __init__(self, name='', op='', value=None):
        self.op = op
        self.name = name
        self.value = value
    
    @classmethod
    def eq(cls, name, value) -> 'Comparator':
        return cls(name, '==', value)
    
    @classmethod
    def ne(cls, name, value) -> 'Statement':
        return NOT(cls.eq(name, value))
    
    @classmethod
    def lt(cls, name, value) -> 'Comparator':
        return cls(name, '<', value)
    
    @classmethod
    def le(cls, name, value) -> 'Comparator':
        return cls(name, '<=', value)
    
    @classmethod
    def gt(cls, name, value) -> 'Comparator':
        return cls(name, '>', value)
    
    @classmethod
    def ge(cls, name, value) -> 'Comparator':
        return cls(name, '>=', value)
    
    def make_query(self) -> str:
        return "{} {} {}".format(self.name, self.op, self.value)


class OrderBy(Statement):
    def __init__(self, orderers: List[Tuple[str, Literal['ASC', 'DESC']]]):
        self.orderers = orderers

    def make_query(self) -> str:
        return "ORDER BY {}".format(", ".join(["{} {}".format(*e) for e in self.orderers]))


class Limit(Statement):
    def __init__(self, row_count, offset=0):
        self.row_count = row_count
        self.offset = offset

    def make_query(self) -> str:
        return "LIMIT {},{}".format(self.offset, self.row_count)


class Query(Statement):
    pass


class SelectQuery(Query):
    def __init__(self, table_name: str, comparator: Union[Comparator, NoneType] = None, orderby: Union[OrderBy, NoneType] = None, limit: Union[Limit, NoneType] = None):
        self.table_name = table_name
        self.comparator = comparator
        self.orderby = orderby
        self.limit = limit

    def where(self, comparator: Comparator) -> 'SelectQuery':
        if self.comparator is None:
            self.comparator = comparator
        else:
            self.comparator = AND(self.comparator, comparator)
        return self

    def limit(self, row_count, offset=0) -> 'SelectQuery':
        self.limit = Limit(row_count, offset=offset)
        return self

    def orderby(self, *additional_orderby_pairs: Tuple) -> 'SelectQuery':
        if self.orderby is None:
            self.orderby = OrderBy(additional_orderby_pairs)
        else:
            self.orderby.column_order_pair.extend(additional_orderby_pairs)
        return self

    def make_query(self) -> str:
        s = "SELECT * FROM {}".format(self.table_name)
        if self.comparator is not None:
            # the spaces are intentional for spacing
            s += ' WHERE ' + self.comparator.make_query()
        if self.orderby is not None:
            s += ' ' + self.orderby.make_query()
        if self.limit is not None:
            s += ' ' + self.limit.make_query()
        return s

    def execute(self, database) -> List[dict]:
        return database._select(self.make_query())
