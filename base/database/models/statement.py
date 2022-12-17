import abc
from typing import List, Tuple, Literal


# Base Classes

class Statement(abc.ABC):
    @abc.abstractmethod
    def make_query(self):
        pass
    
    def __repr__(self):
        return "<Statement>"
    
    def __str__(self):
        return self.make_query()
    
    def __and__(self, other):
        return AND(self, other)
    
    def __or__(self, other):
        return OR(self, other)


class BaseComparator(Statement):
    pass

class BaseOperator(Statement):
    pass


class UnaryOperator(BaseOperator):
    OPERATOR = ''
    def __init__(self, statement:Statement):
        self.statement = statement
    
    def make_query(self):
        return '{} {}'.format(self.__class__.OPERATOR, self.statement)


class BinaryOperator(BaseOperator):
    OPERATOR = ''
    def __init__(self, left:Statement, right:Statement):
        self.left = left
        self.right = right
    
    def make_query(self):
        return '{} {} {}'.format(self.left.make_query(), self.__class__.OPERATOR, self.right.make_query())


class JoinOperator(BinaryOperator):
    "Similiar to BinaryOperator, but with no limit for statements"
    OPERATOR = ''
    def __init__(self, *statements):
        self.statements = statements
    
    def make_query(self):
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
    def eq(cls, name, value):
        return cls(name, '==', value)
    
    @classmethod
    def ne(cls, name, value):
        return NOT(cls.eq(name, value))
    
    @classmethod
    def lt(cls, name, value):
        return cls(name, '<', value)
    
    @classmethod
    def le(cls, name, value):
        return cls(name, '<=', value)
    
    @classmethod
    def gt(cls, name, value):
        return cls(name, '>', value)
    
    @classmethod
    def ge(cls, name, value):
        return cls(name, '>=', value)
    
    def make_query(self):
        return "{} {} {}".format(self.name, self.op, self.value)


class OrderBy(Statement):
    def __init__(self, column_order_pair: List[Tuple[str, Literal['ASC', 'DESC']]]):
        self.column_order_pair = column_order_pair

    def make_query(self):
        return "ORDER BY {}".format(", ".join(["{} {}".format(*e) for e in self.column_order_pair]))


class Limit(Statement):
    def __init__(self, row_count, offset=0):
        self.row_count = row_count
        self.offset = offset

    def make_query(self):
        return "LIMIT {},{}".format(self.offset, self.row_count)


class Query(Statement):
    pass


class SelectQuery(Query):
    def __init__(self, table_name, comparator=None, orderby=None, limit=None):
        self.table_name = table_name
        self.comparator = comparator
        self.orderby = orderby
        self.limit = limit

    def where(self, comparator):
        if self.comparator is None:
            self.comparator = comparator
        else:
            self.comparator = AND(self.comparator, comparator)
        return self

    def limit(self, *args, **kwargs):
        self.limit = Limit(*args, **kwargs)
        return self

    def orderby(self, *additional_orderby_pairs):
        if self.orderby is None:
            self.orderby = OrderBy(additional_orderby_pairs)
        else:
            self.orderby.column_order_pair.extend(additional_orderby_pairs)
        return self

    def make_query(self):
        s = "SELECT * FROM {}".format(self.table_name)
        if self.comparator is not None:
            # the spaces are intentional for spacing
            s += ' WHERE ' + self.comparator.make_query()
        if self.orderby is not None:
            s += ' ' + self.orderby.make_query()
        if self.limit is not None:
            s += ' ' + self.limit.make_query()
        return s

    def execute(self, database):
        return database._select(self.make_query())
