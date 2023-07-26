r"""Fixtures for testing PySIMS."""

# Standard library
import sys

# Third Party
import pytest

# Local
from pysims.config import PLATFORM_SYSTEM_USERNAME_ENV_VARS


@pytest.fixture()
def mocked_system_username_env_var(monkeypatch: pytest.MonkeyPatch) -> str:
    r"""Mocks the system environment variable that contains the username of the PySIMS user.

    Uses `sys.platform` to map the platform to the system username environment variable.

    Platfrom  Env var     OS
    --------  -------     -------
    linux     USER        Linux
    win32     USERNAME    Windows
    cygwin    USERNAME    Windows
    darwin    USERNAME    MacOS

    Returns
    -------
    username : str
        The mocked username.
    """

    env_var = PLATFORM_SYSTEM_USERNAME_ENV_VARS.get(sys.platform)

    if env_var is None:
        error_msg = (
            f'Environment variable for platform {sys.platform} does not exist!\n'
            f'Mapping of platform to system username env var: {PLATFORM_SYSTEM_USERNAME_ENV_VARS}'
        )
        raise KeyError(error_msg)

    username = 'synyster.gates'
    monkeypatch.setenv(env_var, username)

    return username
