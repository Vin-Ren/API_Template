from functools import wraps

from types import NoneType
from typing import Dict, List, Any, Tuple, Union, Callable

from .exception import MissingAttribute, FailedCheck
from .placeholder import LibraryPlaceholder


def require_attrs(required_attr_names: List[str]):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attr in required_attr_names:
                if not hasattr(self, attr):
                    raise MissingAttribute("Required attribute '%(attrname)s' is missing from decorated instance. [hasattr(%(instance)s, %(attrname)s) => False]" % dict(instance=str(self), attrname=attr))
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def check_attrs(__checks: Dict[str, Tuple[callable, BaseException]], *, _ignore_missing_attrs=True, **kwargs: Dict[str,Tuple[callable, BaseException]]):
    __checks.update(kwargs)
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attr, (check, exception) in __checks.items():
                if hasattr(self, attr):
                    if not check(getattr(self, attr)):
                        raise exception from FailedCheck("Check applied on %(attrname)s failed. [check(%(value)s) => False]" % dict(attrname=attr, value=getattr(self, attr)))
                else:
                    if _ignore_missing_attrs:
                        continue
                    raise MissingAttribute("Required attribute '%(attrname)s' is missing from decorated instance. [hasattr(%(instance)s, %(attrname)s) => False]" % dict(instance=str(self), attrname=attr))
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def handle_exception(handler: Callable[[BaseException], NoneType], excepted: Union[BaseException, Tuple[BaseException]] = BaseException):
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
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for lib in libs:
                if issubclass(lib, LibraryPlaceholder):
                    lib.__raise_not_implemented__()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def cached(naive_cache=False, initial_cache=None, fallback_to_initial=False):
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
    optional_callable_value = lambda x: x() if callable(x) else x
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            rv = func(*args, **kwargs)
            return rv if not rv in values_for_default else optional_callable_value(value_or_getter)
        return wrapped
    return decorator
