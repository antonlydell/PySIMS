r"""The exception hierarchy of PySIMS."""

# Standard library
from typing import Any


class PySIMSError(Exception):
    r"""The base Exception of PySIMS.

    Parameters
    ----------
    message : str
        The exception message.

    data : Any, default None
        Optional extra data to include in the exception.
    """

    def __init__(self, message: str, data: Any = None) -> None:
        self.data = data
        super().__init__(message)


# ===============================================================
# Config errors
# ===============================================================


class ConfigError(PySIMSError):
    """Errors related to the configuration of the program."""
