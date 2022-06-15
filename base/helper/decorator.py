from functools import wraps, update_wrapper
import time

from types import FunctionType, NoneType
from typing import Dict, List, Any, Tuple, Union, Callable

from requests import Response

from .exception import MissingAttribute, FailedCheck
from .placeholder import LibraryPlaceholder


def require_attrs(required_attr_names: List[str]):
    """Checks whether the instance has all the required attributes"""
    def decorator(func):
        """Wraps a function, performs a check to make sure all required attributes are present in the instance."""
        if hasattr(func, '__required_attrs'):
            func.__required_attrs.extend(required_attr_names)
            return func
        func.__required_attrs = required_attr_names.copy()
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attr in func.__required_attrs:
                if not hasattr(self, attr):
                    raise MissingAttribute("Required attribute '%(attrname)s' is missing from decorated instance. [hasattr(%(instance)s, %(attrname)s) => False]" % dict(instance=str(self), attrname=attr))
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def check_attrs(__checks: Dict[str, Union[Tuple[callable, BaseException], Any]], *, _ignore_missing_attrs=True, **kwargs: Dict[str, Union[Tuple[callable, BaseException], Any]]):
    """
    Applies all supplied checks to their corresponding target attribute, and if they failed, raise the supplied exception.
    Checks are passed in as a positional only dictionary or keyword arguments.
    
    
    Possible checks structures:
    - {attribute_name: (check_or_value, exception_instance)} or @check_attrs(attribute_name=(check_or_value, exception_instance))
    - {attribute_name: check_or_value} or @check_attrs(attribute_name=check_or_value)
    """
    __checks.update(kwargs)
    def decorator(func):
        """Wraps a function, performs a check to make sure all required (or available) attributes complies with their checks or values, if they are not, raise their corresponding exception if given."""
        if hasattr(func, '__attrs_checks'):
            func.__attrs_checks.update(__checks)
            return func
        func.__attrs_checks = __checks.copy()
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attr, check_and_optional_exception in func.__attrs_checks.items():
                if hasattr(self, attr):
                    if isinstance(check, tuple):
                        check, *_, exception = check_and_optional_exception
                    else:
                        check, exception = (check_and_optional_exception, FailedCheck())
                        
                    if callable(check):
                        if not check(getattr(self, attr)):
                            raise exception from FailedCheck("Check applied on %(attrname)s failed. [check(%(value)s) => False]" % dict(attrname=attr, value=getattr(self, attr)))
                    else:
                        if not getattr(self, attr) == check:
                            raise exception from FailedCheck("Check applied on %(attrname)s failed. [(%(value)s == %(check)s) => False]" % dict(attrname=attr, value=getattr(self, attr)), check=check)
                else:
                    if _ignore_missing_attrs:
                        continue
                    raise MissingAttribute("Required attribute '%(attrname)s' is missing from decorated instance. [hasattr(%(instance)s, %(attrname)s) => False]" % dict(instance=str(self), attrname=attr))
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def handle_exception(handler: Callable[[BaseException], NoneType], excepted: Union[BaseException, Tuple[BaseException]] = BaseException):
    """Wraps the call to the function in a try-except statement. if the supplied 'excepted' argument is catched, then calls handler with catched exception."""
    def decorator(func):
        """Wraps a function and catch exceptions, which if known, will be passed to given handler."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except excepted as exception:
                handler(exception)
        return wrapper
    return decorator


def create_exception_handler(handler: Callable[[BaseException], NoneType], excepted: Union[BaseException, Tuple[BaseException]] = BaseException):
    """Wraps handle_exception, returns the decorator created from handle_exception. Useful for repetitive use of handle_exception decorator."""
    return handle_exception(handler, excepted)


def exception_handler(excepted = BaseException, *extra_excepted):
    """
    Wraps create_exception_handler function, decorate a handler function with this to convert it to a decorator.
    
    
    Can be used in two ways:
    
    Without arguments:
    >>> @exception_handler
    ... def handler(exception):
    ...     pass
    
    With arguments:
    >>> @exception_handler(ExceptionName [, OtherPossibleException, ...])
    ... def handler(exception):
    ...    pass
    """
    if isinstance(excepted, FunctionType):
        """
        If used like:
        @exception_handler
        def handler(exception):
            pass
        """
        return create_exception_handler(excepted,BaseException)
    else:
        """
        If used like:
        @exception_handler(ExceptionName, OtherPossibleException)
        def handler(exception):
            pass
        """
        if isinstance(excepted, (Tuple, List)):
            excepted = excepted + extra_excepted
        else:
            excepted = [excepted] + extra_excepted
        
        def decorator(func):
            """Decorator when exception_handler is used with arguments."""
            return create_exception_handler(func, excepted)
        return decorator


def require_libs(libs: List[type]):
    """Checks whether supplied libraries are a subclass of LibraryPlaceholder, if they are then calls the __raise_not_implemented__ method of the placeholder, else calls the function and returns its return value."""
    def decorator(func):
        """Wraps a function, Performs a check to make sure all required libraries are not dummy libraries, else raises NotInstalled exception."""
        if hasattr(func, '__required_libs'):
            func.__required_libs.update(libs)
            return func
        func.__required_libs = libs.copy()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            for lib in func.__required_libs:
                if issubclass(lib, LibraryPlaceholder):
                    lib.__raise_not_implemented__()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def cached(naive_cache=False, initial_cache=None, fallback_to_initial=False):
    """
    Caches function return value.
    if naive_cache is true, then it caches a result for any given args and kwargs pair.
    if fallback_to_initial is True then you need to supply an initial_cache value. this would be used as a fallback value for dict.get method.
    """
    initial_cache_key = '__INITIALIZED_CACHE__'
    if fallback_to_initial and initial_cache is None:
        raise RuntimeError("to use fallback_to_initial, you need to supply initial_cache.")
        
    def decorator(func):
        """Wraps a function, Caches the return value of wrapped function, to reduce actual call frequency to wrapped function."""
        func._cached_results = {} if initial_cache is None else {('cached' if naive_cache else initial_cache_key):initial_cache}
        @wraps(func)
        def wrapped(*args, recache=False, **kwargs):
            key_for_cache = 'cached' if naive_cache else 'args={};kwargs={}'.format(args, kwargs)
            if not (key_for_cache in func._cached_results) and not (fallback_to_initial and initial_cache_key in func._cached_results) or recache:
                res = func(*args, **kwargs)
                func._cached_results[key_for_cache] = res
            return func._cached_results.get(key_for_cache, func._cached_results.get(initial_cache_key))
        return wrapped
    return decorator


def timed_cache(lifespan=60, naive_cache=False):
    """Like cached, but resets cached response after supplied lifespan in seconds(s). Does not support initial cache."""
        
    def decorator(func):
        """Wraps a function, Caches the return value of wrapped function, to reduce actual call frequency to wrapped function."""
        func._cache_lifespan = lifespan
        func._cached_results = {}
        @wraps(func)
        def wrapped(*args, recache=False, **kwargs):
            key_for_cache = 'cached' if naive_cache else 'args={};kwargs={}'.format(args, kwargs)
            if not (key_for_cache in func._cached_results and (round(time.time()-func._cached_results[key_for_cache][0]) < func._cache_lifespan)) or recache:
                res = func(*args, **kwargs)
                func._cached_results[key_for_cache] = (time.time(), res)
            return func._cached_results.get(key_for_cache)[1]
        return wrapped
    return decorator


def defaults(value_or_getter: Union[Any, callable] = None, values_for_default: list = [None]):
    """Calls the function, and if the return value is in supplied 'values_for_default', then return value from value_or_getter, else return the function return value"""
    optional_callable_value = lambda x: x() if callable(x) else x
    def decorator(func):
        """Wraps a function, evaluates the return value of function, if in values_for_default, then gets value from value_or_getter."""
        @wraps(func)
        def wrapped(*args, **kwargs):
            rv = func(*args, **kwargs)
            return rv if not rv in values_for_default else optional_callable_value(value_or_getter)
        return wrapped
    return decorator


def convert_to(factory_or_class, iterable=False, jsonify=True, ignore_status=False, factorize_all=True):
    """
    Use the given factory to process the return value of given function. There are some preprocessor to the return value before being passed into the factory.
    
    Params
    ------
    iterable: bool
        Whether the return value of decorated function is iterable to be passed to factory. if true, similiar to map(factory, return_value) else factory(return_value)
    jsonify: bool
        Whether to try to convert return value to json or not.
    ignore_status: bool
        Whether to proceed jsonification to a response if the status is not OK.
    factorize_all: bool
        Whether to factorize all return value, even None-like values such as: None, empty list, empty dict, etc.
    """
    def decorator(func):
        """Wraps a function, converts the return value of wrapped function with the factory_or_class and the other options supplied."""
        if iterable:
            def wrapper(*args, **kwargs):
                rv = func(*args, **kwargs)
                rv = rv.json() if jsonify and isinstance(rv, Response) and (rv.ok or ignore_status) else rv
                if rv or factorize_all:
                    return [factory_or_class(entry) for entry in rv]
        else:
            def wrapper(*args, **kwargs):
                rv = func(*args, **kwargs)
                rv = rv.json() if jsonify and isinstance(rv, Response) and (rv.ok or ignore_status) else rv
                if rv or factorize_all:
                    return factory_or_class(rv)
        return update_wrapper(wrapper, func)
    return decorator


# Aliases Section For Other Naming Styles
requireAttrs = require_attrs
checkAttrs = check_attrs
handleException = handle_exception
createExceptionHandler = create_exception_handler
exceptionHandler = exception_handler
asExceptionHandler = as_exception_handler = exception_handler # To avoid naming collisions
requireLibs = require_libs
timedCache = timed_cache
convertTo = convert_to
