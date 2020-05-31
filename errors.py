class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoFileError(Error):
    """Raised when file does not exists"""
    pass