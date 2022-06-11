

class BaseHelperException(BaseException):
    pass


class MissingAttribute(BaseHelperException):
    pass

class MissingLib(BaseHelperException):
    pass

class FailedCheck(BaseHelperException, AssertionError):
    pass
