from functools import wraps, update_wrapper

from types import NoneType
from typing import Dict, List, Any, Tuple, Union, Callable

from requests import Response

from .exception import MissingAttribute, FailedCheck
from .placeholder import LibraryPlaceholder


def require_attrs(required_attr_names: List[str]):
    """Checks whether the instance has all the required attributes"""
    def decorator(func):
        
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
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except excepted as exception:
                handler(exception)
        return wrapper
    return decorator


def require_libs(libs: List[type]):
    """Checks whether supplied libraries are a subclass of LibraryPlaceholder, if they are then calls the __raise_not_implemented__ method of the placeholder, else calls the function and returns its return value."""
    def decorator(func):
        
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


def defaults(value_or_getter: Union[Any, callable] = None, values_for_default: list = [None]):
    """Calls the function, and if the return value is in supplied 'values_for_default', then return value from value_or_getter, else return the function return value"""
    optional_callable_value = lambda x: x() if callable(x) else x
    def decorator(func):
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
