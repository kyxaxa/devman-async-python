class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoFileError(Error):
    """Exception raised when file file_path does not exists

    Attributes:
        file_path -- input file_path which caused the error
        message -- explanation of the error
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.message = f'NO FILE {file_path}'
        super().__init__(self.message)
