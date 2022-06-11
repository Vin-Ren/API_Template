

class BaseHelperException(BaseException):
    pass


class MissingAttribute(BaseHelperException):
    """An attribute is not found in an instance."""

class MissingLib(BaseHelperException):
    """A library is missing."""

class FailedCheck(BaseHelperException, AssertionError):
    """A check has failed."""
