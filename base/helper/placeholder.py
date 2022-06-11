
from .exception import MissingLib


class LibraryPlaceholder:
    """A placeholder for an optional library."""
    @classmethod
    def __raise_not_implemented__(cls):
        raise MissingLib("Module '{}' is not found/installed, this feature is disabled.".format(cls.__name__))
