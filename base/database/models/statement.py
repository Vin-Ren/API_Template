import abc


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


class UnaryOperator(BaseComparator):
    OPERATOR = ''
    def __init__(self, statement:Statement):
        self.statement = statement
    
    def make_query(self):
        return '{} {}'.format(self.__class__.OPERATOR, self.statement)


class BinaryOperator(BaseComparator):
    OPERATOR = ''
    def __init__(self, left:Statement, right:Statement):
        self.left = left
        self.right = right
    
    def make_query(self):
        return '{} {} {}'.format(self.left.make_query(), self.__class__.OPERATOR, self.right.make_query())

# Operators

class NOT(UnaryOperator):
    OPERATOR = 'NOT'

class OR(BinaryOperator):
    OPERATOR = 'OR'

class AND(BinaryOperator):
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
