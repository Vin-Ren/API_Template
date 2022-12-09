

from collections import namedtuple
from enum import Enum
from functools import wraps
from typing import Any, Callable, List, Tuple, Union, Dict


OptCallable = lambda x: x() if callable(x) else x
HookEntry = namedtuple('HookEntry', ['func','priority'])
ExceptionHandler = namedtuple('ExceptionHandler', ['func', 'exception'])


class OrderedList(list):
    ORDER_KEY=lambda x:x
    def reorder(self):
        self.sort(key=self.__class__.ORDER_KEY)
    
    def append(self, __object):
        rv = super().append(__object)
        self.reorder()
        return rv
    def extend(self, __iterable):
        rv = super().extend(__iterable)
        self.reorder()
        return rv
    def __iadd__(self, __x):
        rv = super().__iadd__(__x)
        self.reorder()
        return rv


class Priority(Enum):
    """
    To categorize the priority of execution for callback hooks. 
    LOWEST & HIGHEST must be unique (No constraints programmatically, however it is recommended). LOWEST is guaranteed to be executed last and vice versa.
    but [LOW, NORMAL, HIGH] are not unique, but callbacks with the same priority do not have any execution order guarantee.
    Callback order: HIGHEST > HIGH > NORMAL > LOW > LOWEST.
    """
    LOWEST=1
    LOW=2
    NORMAL=3
    HIGH=4
    HIGHEST=5


class PriorityOrderedList(OrderedList):
    ORDER_KEY=lambda entry:entry.priority.value


class WrapperCls:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self._name = func.__repr__
        self.before_hooks: PriorityOrderedList[HookEntry] = PriorityOrderedList()
        self.after_hooks: PriorityOrderedList[HookEntry] = PriorityOrderedList()
        self.preprocessors: PriorityOrderedList[HookEntry] = PriorityOrderedList()
        self.postprocessors: PriorityOrderedList[HookEntry] = PriorityOrderedList()
        self.exception_handlers: PriorityOrderedList[ExceptionHandler] = PriorityOrderedList()
        self._default = None
    
    # Properties for abstraction layer
    @property
    def name(self):
        return OptCallable(self._name)
    @name.setter
    def name(self, replacer):
        self._name=replacer
    @property
    def default(self):
        return OptCallable(self._default)
    @default.setter
    def default(self, replacer):
        self._default=replacer
    
    # Method Chainings
    def set_name(self, replacer):
        self.name=replacer
        return self
    def set_default(self, replacer):
        self.default=replacer
        return self
    def extend_before_hooks(self, hooks: List[HookEntry[Callable, Priority]]):
        self.before_hooks.extend(hooks)
        return self
    def extend_after_hooks(self, hooks: List[HookEntry[Callable, Priority]]):
        self.after_hooks.extend(hooks)
        return self
    def extend_preprocessors(self, hooks: List[HookEntry[Callable[[Tuple, Dict], Tuple[Tuple, Dict]], Priority]]):
        self.preprocessors.extend(hooks)
        return self
    def extend_postprocessors(self, hooks: List[HookEntry[Callable[[Any], Any], Priority]]):
        self.postprocessors.extend(hooks)
        return self
    def extend_exception_handlers(self, handlers: List[ExceptionHandler[Callable[[BaseException], None], BaseException]]):
        self.exception_handlers.extend(handlers)
        return self
    
    # Modifiers
    def __repr__(self):
        return self.name
    def __str__(self):
        return self.__repr__()
    def __call__(self, *args, **kwargs):
        rv=self.default
        try:
            [he.func()for he in self.before_hooks[::-1]]
            for he in self.preprocessors[::-1]:
                (args, kwargs) = he.func(args, kwargs)
            rv = self.func(*args, **kwargs)
            for he in self.postprocessors[::-1]:
                rv = he.func(rv)
            [he.func()for he in self.after_hooks[::-1]]
        except BaseException as exc:
            for handler in self.exception_handlers:
                if isinstance(exc, handler.exception):
                    handler(exc)
        return rv
    
    # Utilities Class Methods
    @classmethod
    def get_wrapped(cls, func):
        if not isinstance(func, cls):
            func = cls(func)
        return func


def name(name: Union[str, Callable]):
    "Wraps a function in a wrapper class, gives functionality for a custom __repr__ method to be used."
    def decor(func):
        return WrapperCls.get_wrapped(func).set_name(name)
    return decor


def before(callback, priority:Priority):
    """Adds the given callback with the set priority to the function's before_hooks."""
    def decor(func):
        return WrapperCls.get_wrapped(func).extend_before_hooks([HookEntry(callback, priority)])
    return decor

def after(callback, priority:Priority):
    """Adds the given callback with the set priority to the function's after_hooks."""
    def decor(func):
        return WrapperCls.get_wrapped(func).extend_after_hooks([HookEntry(callback, priority)])
    return decor


def preprocessor(callback, priority:Priority):
    """Adds a preprocessor to the wrapped function."""
    def decor(func):
        return WrapperCls.get_wrapped(func).extend_preprocessors([HookEntry(callback, priority)])
    return decor


def postprocessor(callback, priority:Priority):
    """Adds a postprocessor to the wrapped function."""
    def decor(func):
        return WrapperCls.get_wrapped(func).extend_postprocessors([HookEntry(callback, priority)])
    return decor


class DecorWrapper:
    def __init__(self, wrapper_name, enum_member_map, decor: Callable[[Callable,Priority], Callable], docs=''):
        self.wrapper_name=wrapper_name
        self.enum_member_map=enum_member_map
        self.decor = decor
        self.__doc__ = docs
    def __getattribute__(self, __name: str):
        try:
            return super().__getattribute__(__name)
        except AttributeError:
            return (lambda func: self.decor(func, self.enum_member_map[__name.upper()]))
    def __repr__(self):
        return "<{} DecorWrapper>".format(self.wrapper_name)

"""
Wrappers for their corresponding decorator.
Example:
@Before.NORMAL(callback)
def function():
    ...

is the same as:
@before(callback, Priority.NORMAL)
def function():
    ...
"""
Before = DecorWrapper('Before', Priority._member_map_, before)
After = DecorWrapper('After', Priority._member_map_, after)
Preprocessor = DecorWrapper('Preprocessor', Priority._member_map_, preprocessor)
Postprocessor = DecorWrapper('Postprocessor', Priority._member_map_, postprocessor)



if __name__=='__main__':
    cb = lambda: print("cb here")
    cb1 = lambda: print("cb1 here")
    cb2 = lambda: print("cb2 here")
    cb3 = lambda: print("cb3 here")
    cb4 = lambda: print("cb4 here")
    
    pre1 = lambda args,kw:[print('pre1 processing', args, kw), (args,kw)][1]
    pre2 = lambda args,kw:[print('pre2 processing', args, kw), (args,kw)][1]
    pre3 = lambda args,kw:[print('pre3 processing', args, kw), (args,kw)][1]
    pre4 = lambda args,kw:[print('pre4 processing', args, kw), (args,kw)][1]
    pre5 = lambda args,kw:[print('pre5 processing', args, kw), (args,kw)][1]
    
    post1 = lambda rv:[print('post1 processing', rv), rv][1]
    post2 = lambda rv:[print('post2 processing', rv), rv][1]
    post3 = lambda rv:[print('post3 processing', rv), rv][1]
    post4 = lambda rv:[print('post4 processing', rv), rv][1]
    post5 = lambda rv:[print('post5 processing', rv), rv][1]

    @Before.HIGHEST(cb4)
    @Before.HIGH(cb3)
    @Before.NORMAL(cb2)
    @Before.LOW(cb1)
    @Before.LOWEST(cb)
    
    @After.HIGHEST(cb)
    @After.HIGH(cb1)
    @After.NORMAL(cb2)
    @After.LOW(cb3)
    @After.LOWEST(cb4)
    
    @Preprocessor.HIGHEST(pre5)
    @Preprocessor.HIGH(pre4)
    @Preprocessor.NORMAL(pre3)
    @Preprocessor.LOW(pre2)
    @Preprocessor.LOWEST(pre1)
    
    @Postprocessor.HIGHEST(post1)
    @Postprocessor.HIGH(post2)
    @Postprocessor.NORMAL(post3)
    @Postprocessor.LOW(post4)
    @Postprocessor.LOWEST(post5)
    
    @name('<TestFunction>')
    def f(arg1, arg2, arg3=1): return [print("f here"), 'retval'][1]
    print("function name:", f)
    # print('Before hooks:', f.before_hooks, '\nAfter hooks:', f.after_hooks, '\nPreprocessors:', f.preprocessors, '\nPostprocessors:', f.postprocessors)
    print('\n---- Executing f ----')
    rv=f('arg1','arg2',arg3='arg3 val')
    print("--------------\nreturn value:", rv, "\n---- DONE ----")
