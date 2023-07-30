r"""The config module defines the PySIMS configuration.

The module provides the interface for handling the program's configuration.
The configuration constants of PySIMS are also stored here.
"""

# Standard Library
from enum import IntEnum, StrEnum
import logging
import os
from pathlib import Path
import sys
from typing import Any, ClassVar, Sequence

# Third Party
import click
from pydantic import BaseModel, BaseSettings, Field, HttpUrl, validator, ValidationError
from pydantic.env_settings import SettingsSourceCallable
from sqlalchemy.engine import make_url, URL  # type: ignore

# Local
from . import exceptions

logger = logging.getLogger(__name__)


# ===============================================================
# Constants
# ===============================================================

# Context settings to apply to the main function of the click application.
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=1000)

# Name of the program.
PROG_NAME = 'pysims'

# The name of the program displayed in help texts.
PROG_NAME_DISPLAY = 'PySIMS'

# The home directory of the program.
PROG_DIR = Path.home() / f'.{PROG_NAME}'

# The name of the configuration file.
CONFIG_FILENAME = f'.{PROG_NAME}.toml'

# The full path to the user configuration file.
USER_CONFIG_FILE_PATH = PROG_DIR / CONFIG_FILENAME

# The displayable name of the full path to the user config file.
USER_CONFIG_FILE_PATH_DISPLAY = click.format_filename(USER_CONFIG_FILE_PATH)

# The name of the environment variable, which points to a config file.
ENV_CONFIG_FILE_ENV_VAR = 'PYSIMS_CONFIG_FILE'

# The name of the default SQLite database.
SQLITE_DEFAULT_DB_FILENAME = f'{PROG_NAME}.db'

# The default path to the SQLite database.
SQLITE_DEFAULT_DB_FILE_PATH = PROG_DIR / SQLITE_DEFAULT_DB_FILENAME

# The displayable name of the full path to the default SQLite database.
SQLITE_DEFAULT_DB_FILE_PATH_DISPLAY = click.format_filename(SQLITE_DEFAULT_DB_FILE_PATH)

# The default name of the log file.
LOGGING_DEFAULT_FILENAME = f'{PROG_NAME}.log'

# The default log file directory.
LOGGING_DEFAULT_DIR = PROG_DIR / 'logs'

# The full path to the default log file.
LOGGING_DEFAULT_FILE_PATH = LOGGING_DEFAULT_DIR / LOGGING_DEFAULT_FILENAME

# The displayable name of the full path to the default log file.
LOGGING_DEFAULT_FILE_PATH_DISPLAY = click.format_filename(LOGGING_DEFAULT_FILE_PATH)

# The default format of a log message.
LOGGING_DEFAULT_FORMAT = (
    r'%(asctime)s|%(name)s|%(levelname)s|%(funcName)s|Line:%(lineno)s|%(message)s'
)

# The default date format of a log message.
LOGGING_DEFAULT_DATETIME_FORMAT = r'%Y-%m-%dT%H:%M:%S'

# Mapping of platform to system username environment variable.
PLATFORM_SYSTEM_USERNAME_ENV_VARS = {
    'linux': 'USER',
    'win32': 'USERNAME',
    'cygwin': 'USERNAME',  # Windows
    'darwin': 'USERNAME',  # MacOS
}


# ===============================================================
# Enums
# ===============================================================


class LogLevels(IntEnum):
    r"""The available log levels."""

    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Streams(StrEnum):
    r"""The available input and output streams."""

    STDIN = 'stdin'
    STDOUT = 'stdout'
    STDERR = 'stderr'


# ===============================================================
# Models
# ===============================================================

available_databases: dict = {}  # dict[str, Database]
available_sensor_portals: dict = {}  # dict[str, SensorPortal]


class BaseConfigModel(BaseModel):
    r"""The BaseModel that all configuration models inherit from."""

    def __init__(self, **kwargs) -> None:
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            raise exceptions.ConfigError(str(e)) from None


class UserSection(BaseConfigModel):
    r"""The user section of the configuration.

    Parameters
    ----------
    username_from_env_var : bool, default True
        If True `username` will take its value from the system username
        environment variable and override the supplied value to `username`.

    username : str | None, default None
        The username of the user.

    password : str | None, default None
        The password of the user.

    api_key : str | None, default None
        The API key used to authenticate the user.

    session_key_expiry : int, default 900
        The number of seconds until the active session key expires.
        The default is 900 s = 15 min.

    set_session_key_env_var : bool, default True
        If True the session key environment variable `PYSIMS_SESSION_KEY` will be set to
        the value of the active session key automatically by PySIMS upon user login.
        If False the environment variable will not be set.
    """

    username_from_env_var: bool = True
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    session_key_expiry: int = Field(default=900, ge=0)
    set_session_key_env_var: bool = True

    @validator('username', always=True)
    def set_username(cls, v: str | None, values) -> str | None:
        r"""Set the value of `username`.

        If `username_from_env_var` is True then the `username` should be set to the
        value of the system username environment variable and override the input
        value to `username`.
        """

        if values['username_from_env_var'] is False:
            return v

        if (env_var := PLATFORM_SYSTEM_USERNAME_ENV_VARS.get(sys.platform)) is None:
            error_msg = (
                f'No defined username environment variable for {sys.platform=}.\n'
                f'Mapping of platform to system username env var: {PLATFORM_SYSTEM_USERNAME_ENV_VARS}'
            )
            raise ValueError(error_msg)

        if (new_username := os.getenv(env_var)) is None:
            error_msg = (
                f'Username environment variable {env_var} is not configured on your system! '
                f'Either set the environment variable {env_var} or change the config '
                'key "user.username_from_env_var" from True to False and specify a value '
                'for the config key "user.username".'
            )
            raise ValueError(error_msg)
        else:
            return new_username


class Database(BaseConfigModel):
    r"""The configuration for a database.

    Each type of database should inherit from `Database`.

    Class variables
    ---------------
    name : str
        The name of the database to use for registering the database in the available
        database registry `available_databases`.`available_databases` is a dict that
        maps the database name to its class.

    Parameters
    ----------
    url : str or sqlalchemy.engine.URL
        The SQLAlchemy connection url of the database.
    """

    name: ClassVar[str]

    url: str | URL | None = ''

    def __init_subclass__(cls) -> None:
        r"""Register the class as an available database to use."""

        available_databases[cls.name] = cls
        return super().__init_subclass__()

    @validator('url')
    def validate_url(cls, v: str | URL | None) -> URL | None:
        r"""Validate that the `url` attribute is a correct SQLAlchemy database url."""

        if v is None:
            return v

        try:
            return make_url(v)
        except Exception as e:
            raise ValueError(f'{type(e).__name__} : {e.args[0]}')

    def url_to_string(self, hide_password: bool = True) -> str | None:
        r"""Convert the `url` attribute to string representation.

        Parameters
        ----------
        hide_password : bool, default True
            If the password of the `url` attribute should be masked with ***
            instead of displayed as plain text.

        Returns
        -------
        str | None
            The string representation of the `url` attribute.
            None is returned if the `url` attribute is None.
        """
        if (url := self.url) is None:
            return url
        else:
            return url.render_as_string(hide_password=hide_password)  # type: ignore


class SQLiteDatabase(Database):
    r"""A SQLite database.

    Parameters
    ----------
    path : Path , default SQLITE_DEFAULT_DB_FILE_PATH
        The path to the SQLite database file.
    """

    name: ClassVar[str] = 'sqlite'
    path: Path = SQLITE_DEFAULT_DB_FILE_PATH

    @validator('path')
    def validate_path(cls, v: Path, values) -> Path | Any:
        r"""Validate the `path` attribute."""

        if not v.exists():
            raise ValueError(
                f'The database file path does not exist! path = {click.format_filename(v)}'
            )
        elif v.is_dir():
            raise ValueError(
                f'The database file path must be a file and not a directory! '
                f'path = {click.format_filename(v)}'
            )
        else:
            return v.resolve()


class DatabaseSection(BaseConfigModel):
    r"""The configuration for the database section in the config file.

    Parameters
    ----------
    backend : str, default 'sqlite'
        The SQLAlchemy connection url of the database.

    db_schema : str, default ''
        The schema to use for the database.

    prefix : str, default PROG_NAME
        The prefix to apply to all table names of the database. E.g. <prefix>_<table name>.
        Useful if the program shares a schema with other programs.

    sqlite : SQLiteDatabase
        The configuration for the SQLite database.
    """

    backend: str = 'sqlite'
    db_schema: str = Field(alias='schema', default='')
    prefix: str = PROG_NAME
    sqlite: SQLiteDatabase = Field(default_factory=SQLiteDatabase)

    @validator('backend')
    def validate_backend(cls, v: str) -> str:
        r"""Validate the `backend` attribute."""

        backends = set(available_databases.keys())

        if (backend := v.casefold()) not in backends:
            error_msg = f'{v!r} is not a valid database backend. Valid backends are: {backends}'
            raise ValueError(error_msg)
        else:
            return backend


class SensorPortal(BaseConfigModel):
    r"""The base class for configuration of a sensor portal.

    Each sensor portal should inherit from `SensorPortal`.

    Class variables
    ---------------
    name : str
        The name of the sensor portal to use for registering the portal in the available
        sensor portal registry `available_sensor_portals`. `available_sensor_portals` is
        a dict that maps the sensor portal name to its class.
    """

    name: ClassVar[str]

    def __init_subclass__(cls) -> None:
        r"""Register the class as an available sensor portal to use."""

        available_sensor_portals[cls.name] = cls
        return super().__init_subclass__()


class NetmoreSensorPortal(SensorPortal):
    r"""The configuration of the Netmore sensor portal.

    Parameters
    ----------
    username : str, default ''
        The username of the Netmore portal user.

    password : str, default ''
        The password of the user.

    base_url : HttpUrl, default ''
        The base url of the Netmore portal REST API.

    sensor_id_column : str, default 'dev_eui'
        The column of the sensor that is used to identify a sensor in the Netmore portal.
    """

    name: ClassVar[str] = 'netmore'

    username: str = ''
    password: str = ''
    base_url: HttpUrl = HttpUrl(url='', scheme='https')  # type: ignore
    sensor_id_column: str = 'dev_eui'


class SensorPortalSection(BaseConfigModel):
    r"""The configuration for the portal section in the config file.

    Parameters
    ----------
    portal : str, default 'netmore'
        The default sensor portal to fetch sensor data from.

    netmore : NetmorePortal
        The configuration for the Netmore sensor portal.
    """

    portal: str = 'netmore'
    netmore: NetmoreSensorPortal = Field(default_factory=NetmoreSensorPortal)

    @validator('portal')
    def validate_portal(cls, v: str) -> str:
        r"""Validate the `portal` attribute."""

        portals = set(available_sensor_portals.keys())

        if (portal := v.casefold()) not in portals:
            error_msg = f'{v!r} is not a valid sensor portal. Valid sensor portals are: {portals}'
            raise ValueError(error_msg)
        else:
            return portal


class CsvFileFormat(BaseConfigModel):
    r"""The configuration of a csv file format.

    Parameters
    ----------
    delim : str, default ';'
        The delimter of the csv file.

    encoding : str, default 'UTF-8'
        The character encoding of the csv file.

    extension : str, default '.csv'
        The file extension of the csv file.
    """

    delim: str = ';'
    encoding: str = 'UTF-8'
    extension: str = '.csv'


class ExportSection(BaseConfigModel):
    r"""The configuration of the export section in the config file.

    Parameters
    ----------
    format : str, default 'csv'
        The format to use for data exports.

    creation_datetime : bool, default True
        True if the creation datetime of the exported file should be prepended to the file
        name and False to omit it from the file name.

    creation_datetime_format : str, default r'%y-%m-%dT%H.%M.%S'
        The date format to use for `creation_datetime`.

    output_dir : Path, default Path.cwd()
        The output directory of the exported file.

    csv : CsvFileFormat
        The configuration of the csv export format.
    """

    format: str = 'csv'
    creation_datetime: bool = True
    creation_datetime_format: str = r'%y-%m-%dT%H.%M.%S'
    output_dir: Path = Field(default_factory=Path.cwd)
    csv: CsvFileFormat = Field(default_factory=CsvFileFormat)

    @validator('format')
    def validate_format(cls, v: str) -> str:
        r"""Validate the `format` attribute."""

        formats = {'csv'}

        if (v_case := v.casefold()) not in formats:
            error_msg = f'{v!r} is not a valid export file format. Valid formats are: {formats}'
            raise ValueError(error_msg)
        else:
            return v_case


class LogHandler(BaseConfigModel):
    r"""The base model of a log handler.

    A log handler handles the log messages produced by the program.

    Parameters
    ----------
    disabled : bool, default False
        True if the log handler should be disabled and False to keep it active.

    min_log_level : LogLevels, default LogLevels.INFO
        The minimum log level sent to the log handler.

    format : str, default `LOGGING_DEFAULT_FORMAT`
        The format string of the log message.
        See https://docs.python.org/3/library/logging.html#logrecord-attributes
        for a syntax reference.

    datetime_format : str, default `LOGGING_DEFAULT_DATETIME_FORMAT`
        The format string of the logging timestamp.
        Uses `time.strftime` syntax. See https://docs.python.org/3/library/time.html#time.strftime
        for a syntax reference.
    """

    disabled: bool = False
    min_log_level: LogLevels = LogLevels.INFO
    format: str = LOGGING_DEFAULT_FORMAT
    datetime_format: str = LOGGING_DEFAULT_DATETIME_FORMAT


class StreamLogHandler(LogHandler):
    r"""The stream log handler logs messages to the output streams stdout and or stderr.

    Parameters
    ----------
    streams : Sequence[Streams], default (Streams.STDERR,)
        The output streams to send the log messages to.
        The default `Streams.STDERR` logs to stderr.
    """

    streams: tuple[Streams, ...] = (Streams.STDERR,)

    @validator('streams')
    def deduplicate_streams(cls, v: tuple[Streams, ...]) -> tuple[Streams, ...]:
        r"""Remove duplicates from the `streams` attribute."""

        return tuple(set(v))


class FileLogHandler(LogHandler):
    r"""The file log handler logs messages to a log file.

    Parameters
    ----------
    path : Path, default `LOGGING_DEFAULT_FILE_PATH`
        The path to the log file.

    username_in_filename : bool, default False
        True if the username of the user should be prepended
        to the log filename and False otherwise.
    """

    path: Path = LOGGING_DEFAULT_FILE_PATH
    username_in_filename: bool = False

    @validator('path')
    def validate_path(cls, v: Path) -> Path:
        r"""Validate the `path` attribute."""

        if v.is_dir():
            error_msg = (
                f'The log file path must be a file and not a directory! '
                f'path = {click.format_filename(v)}'
            )
            raise ValueError(error_msg)
        else:
            return v


class LoggingSection(BaseConfigModel):
    r"""The configuration of the logging section in the config file.

    Parameters
    ----------
    disabled : bool, default False
        True if all log handlers should be disabled and False otherwise.

    min_log_level : LogLevels, default LogLevels.INFO
        The minimum log level sent to the log handlers. Used as a fallback
        if a minimum log level is not set on a log handler.

    format : str, default `LOGGING_DEFAULT_FORMAT`
        The format string of the log message.
        See https://docs.python.org/3/library/logging.html#logrecord-attributes
        for a syntax reference.

    datetime_format : str, default `LOGGING_DEFAULT_DATETIME_FORMAT`
        The format string of the logging timestamp.
        Uses `time.strftime` syntax. See https://docs.python.org/3/library/time.html#time.strftime
        for a syntax reference.

    stream : StreamLogHandler
        The configuration of the stream log handler.

    file : FileLogHandler
        The configuration of the file log handler.
    """

    disabled: bool = False
    min_log_level: LogLevels = LogLevels.INFO
    format: str = LOGGING_DEFAULT_FORMAT
    datetime_format: str = LOGGING_DEFAULT_DATETIME_FORMAT
    stream: StreamLogHandler = Field(default_factory=StreamLogHandler)
    file: FileLogHandler = Field(default_factory=FileLogHandler)


class ConfigManager(BaseSettings):
    r"""The `ConfigManager` handles the program's configuration.

    Parameters
    ----------
    editor : str, default ''
        The text editor to use for editing the program's configuration file.
        The default of '' uses the system's default editor.

    user : UserSection
        The user section of the configuration.

    database : DatabaseSection
        The database section of the configuration.

    portal : SensorPortalSection
        The sensor portal section of the configuration.

    export : ExportSection
        The export section of the configuration.

    logging : LoggingSection
        The logging section of the configuration.
    """

    editor: str = ''
    user: UserSection = Field(default_factory=UserSection)
    database: DatabaseSection = Field(default_factory=DatabaseSection)
    portal: SensorPortalSection = Field(default_factory=SensorPortalSection)
    export: ExportSection = Field(default_factory=ExportSection)
    logging: LoggingSection = Field(default_factory=LoggingSection)

    class Config:
        env_prefix = 'pysims_'
        env_nested_delimiter = '__'
        extra = 'ignore'

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            r"""Change the priority order of config sources.

            New order of precedence:
                - 1. Environment variables.
                - 2. Values passed to the initializer.
                - 3. Values loaded from a secrets' file.
            """

            return env_settings, init_settings, file_secret_settings

    def __init__(self, **kwargs) -> None:
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            raise exceptions.ConfigError(str(e)) from None


# ===============================================================
# Functions
# ===============================================================


ConfigDict = dict[str, Any]


def merge_config_dicts(dicts: Sequence[ConfigDict]) -> ConfigDict:
    r"""Merge a sequence of config dictionaries.

    The highest priority dictionary should be the last item in the sequence.
    E.g. dicts[0] < dicts[1] < dicts[2]

    Parameters
    ----------
    dicts : Sequence[ConfigDict]
        The config dictionaries to merge together.
        The highest priority dictionary should be the last item in the sequence.

    Returns
    -------
    merged : ConfigDict
        The result of the merged dictionaries.
    """

    def _merge_config_dicts(
        dicts: Sequence[ConfigDict], to_update: ConfigDict, key_1: str, key_2: str | None = None
    ) -> None:
        r"""Helper function to merge dictionaries.

        Updates the config dict `to_update` inplace with the result of the merge.
        If the result of the merge is an empty dict `to_update` is not updated.

        Parameters
        ----------
        dicts : Sequence[ConfigDict]
            The config dictionaries to merge together.

        to_udpate : ConfigDict
            The dictionary to update with the result of the merge.
            The result is assigned to `key_1` and `key_2` if `key_2`
            is not None.

        key_1 : str
            The top level key to extract from the config dictionaries.

        key_2 : str | None, default None
            The second level key to extract from the config dictionaries.
        """

        result: ConfigDict = {}
        if key_2 is None:
            to_merge = [c.get(key_1, {}) for c in dicts]
        else:
            to_merge = [c.get(key_1, {}).get(key_2, {}) for c in dicts]

        for d in to_merge:
            result |= d  # Update result with data from d and assign to result

        if result:
            if key_2 is None:
                to_update[key_1] = result
            else:
                to_update[key_1][key_2] = result

    merged: ConfigDict = {}
    if (nr_config_dicts := len(dicts)) == 0:
        return merged
    elif nr_config_dicts == 1:
        return dicts[0]
    else:
        pass

    if all(not c for c in dicts):  # If all dicts are empty
        return merged

    # editor
    editor = [e for conf in dicts if (e := conf.get('editor')) is not None]
    merged['editor'] = editor.pop()

    # user section
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='user')

    # database section
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='database')
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='database', key_2='sqlite')

    # portal section
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='portal')
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='portal', key_2='netmore')

    # export section
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='export')
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='export', key_2='csv')

    # logging section
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='logging')
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='logging', key_2='stream')
    _merge_config_dicts(to_update=merged, dicts=dicts, key_1='logging', key_2='file')

    return merged
