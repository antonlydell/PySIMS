r"""Unit tests for the config module."""

# Standard library
from pathlib import Path
import sys
from typing import Any

# Third Party
import pytest
from pydantic import HttpUrl
from sqlalchemy.engine import make_url, URL

# Local
from pysims.config import (
    available_databases,
    available_sensor_portals,
    ConfigManager,
    CsvFileFormat,
    Database,
    DatabaseSection,
    ExportSection,
    FileLogHandler,
    LOGGING_DEFAULT_DATETIME_FORMAT,
    LOGGING_DEFAULT_FILE_PATH,
    LOGGING_DEFAULT_FORMAT,
    LoggingSection,
    LogHandler,
    LogLevels,
    NetmoreSensorPortal,
    SensorPortalSection,
    SQLiteDatabase,
    SQLITE_DEFAULT_DB_FILE_PATH,
    StreamLogHandler,
    Streams,
    UserSection,
)
from pysims import exceptions


# =============================================================================================
# Fixtures
# =============================================================================================


@pytest.fixture()
def default_config(mocked_system_username_env_var: str) -> dict[str, Any]:
    r"""The default configuration of `ConfigManager`."""

    return {
        'editor': '',
        'user': {
            'username_from_env_var': True,
            'username': mocked_system_username_env_var,
            'password': None,
            'api_key': None,
            'session_key_expiry': 900,
            'set_session_key_env_var': True,
        },
        'database': {
            'backend': 'sqlite',
            'schema': '',
            'prefix': 'pysims',
            'sqlite': {'url': '', 'path': SQLITE_DEFAULT_DB_FILE_PATH},
        },
        'portal': {
            'portal': 'netmore',
            'netmore': {
                'username': '',
                'password': '',
                'base_url': HttpUrl(url='', scheme='https'),
                'sensor_id_column': 'dev_eui',
            },
        },
        'export': {
            'format': 'csv',
            'creation_datetime': True,
            'creation_datetime_format': r'%y-%m-%dT%H.%M.%S',
            'output_dir': Path.cwd(),
            'csv': {
                'delim': ';',
                'encoding': 'UTF-8',
                'extension': '.csv',
            },
        },
        'logging': {
            'disabled': False,
            'min_log_level': LogLevels.INFO,
            'format': LOGGING_DEFAULT_FORMAT,
            'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
            'stream': {
                'disabled': False,
                'min_log_level': LogLevels.INFO,
                'format': LOGGING_DEFAULT_FORMAT,
                'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
                'streams': (Streams.STDERR,),
            },
            'file': {
                'disabled': False,
                'min_log_level': LogLevels.INFO,
                'format': LOGGING_DEFAULT_FORMAT,
                'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
                'path': LOGGING_DEFAULT_FILE_PATH,
                'username_in_filename': False,
            },
        },
    }


# =============================================================================================
# Tests
# =============================================================================================


class TestUserSection:
    r"""Tests for the config model `UserSection`.

    The `UserSection` handles the user configuration.
    """

    def test_init_all_values_ok(self) -> None:
        r"""Test to initialize an instance of `UserSection`."""

        # Setup
        # ===========================================================
        data = {
            'username_from_env_var': False,
            'username': 'm.shadows',
            'password': 'ax7',
            'api_key': 'critical_acclaim',
            'session_key_expiry': 0,
            'set_session_key_env_var': False,
        }

        # Exercise
        # ===========================================================
        user = UserSection(**data)

        # Verify
        # ===========================================================
        assert user.dict() == data

        # Clean up - None
        # ===========================================================

    def test_username_from_env_var(self, mocked_system_username_env_var: str) -> None:
        r"""Test to load the username from the system username environment variable.

        The supplied username should be overridden if `username_from_env_var` is True.
        """

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        user = UserSection(username='test', username_from_env_var=True)

        # Verify
        # ===========================================================
        assert user.username == mocked_system_username_env_var

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        'username_env_var',
        (
            pytest.param(
                'USER',
                id='Linux',
                marks=pytest.mark.skipif(
                    condition=not sys.platform.startswith('linux'),
                    reason=f'Linux test cannot run on platform={sys.platform}',
                ),
            ),
            pytest.param(
                'USERNAME',
                id='Windows',
                marks=pytest.mark.skipif(
                    condition=not sys.platform.startswith('win'),
                    reason=f'Windows test cannot run on platform={sys.platform}',
                ),
            ),
            pytest.param(
                'USERNAME',
                id='MacOS',
                marks=pytest.mark.skipif(
                    condition=not sys.platform.startswith('darwin'),
                    reason=f'MacOS test cannot run on platform={sys.platform}',
                ),
            ),
        ),
    )
    @pytest.mark.raises
    def test_username_env_var_missing(
        self, username_env_var: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""Test to load the username from the system username environment variable.

        The expected system username environment variable does not exist.
        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        monkeypatch.delenv(username_env_var)

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            UserSection(username_from_env_var=True)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert (
            username_env_var in error_msg
        ), f'Username env var {username_env_var} not in error message!'

        # Clean up - None
        # ===========================================================

    def test_negative_session_key_expiry(self) -> None:
        r"""Test to supply a negative value for the key `session_key_expiry`.

        `session_key_expiry` should be >= 0. `exceptions.ConfigError` is expected to be raised.
        """

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            UserSection(session_key_expiry=-1)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        # Clean up - None
        # ===========================================================


@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
class TestDatabase:
    r"""Tests for the config model `Database`.

    The `Database` class is the base class for a database configuration.
    """

    @pytest.mark.parametrize(
        'url',
        (
            pytest.param(None, id='None'),
            pytest.param('oracle+cx_oracle://user:pw@myserver:1521/sid', id='str'),
            pytest.param(
                make_url('oracle+cx_oracle://user:pw@myserver:1521/sid'), id='SQLAlchemy URL'
            ),
        ),
    )
    def test_init(self, url: str | URL | None) -> None:
        r"""Test to initialize an instance of `Database`."""

        # Setup
        # ===========================================================
        url_exp = url if url is None else make_url(url)

        # Exercise
        # ===========================================================
        db = Database(url=url)

        # Verify
        # ===========================================================
        assert db.url == url_exp

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_database_url(self) -> None:
        r"""Test to provide an invalid database url.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        url = 'oracle+cx_oracle:://user:pw@myserver:1521/sid'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            Database(url=url)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert url in exc_info_str

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        'url, url_exp, hide_password',
        (
            pytest.param(None, None, False, id='None'),
            pytest.param(
                'oracle+cx_oracle://user:pw@myserver:1521/sid',
                'oracle+cx_oracle://user:***@myserver:1521/sid',
                True,
                id='hide_password=True',
            ),
            pytest.param(
                make_url('oracle+cx_oracle://user:pw@myserver:1521/sid'),
                'oracle+cx_oracle://user:pw@myserver:1521/sid',
                False,
                id='hide_password=False',
            ),
        ),
    )
    def test_url_to_string(
        self, url: str | URL | None, url_exp: str | None, hide_password: bool
    ) -> None:
        r"""Test to convert the `url` attribute to string."""

        # Setup
        # ===========================================================
        db = Database(url=url)

        # Exercise
        # ===========================================================
        url_str = db.url_to_string(hide_password=hide_password)

        # Verify
        # ===========================================================
        assert url_str == url_exp

        # Clean up - None
        # ===========================================================


@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
class TestSQLiteDatabase:
    r"""Tests for the config model `SQLiteDatabase`.

    The `SQLiteDatabase` class defines the configuration for the SQLite database.
    """

    def test_init_with_valid_path(self, tmp_path: Path) -> None:
        r"""Test to create an instance of `SQLiteDatabase` from a valid file path."""

        # Setup
        # ===========================================================
        path = tmp_path / 'pysims.db'
        path.touch()

        # Exercise
        # ===========================================================
        db = SQLiteDatabase(path=path)

        # Verify
        # ===========================================================
        assert db.path == path

        # Clean up - None
        # ===========================================================

    def test_init_with_url(self) -> None:
        r"""Test to create an instance of `SQLiteDatabase` from a SQLAlchemy url."""

        # Setup
        # ===========================================================
        url = make_url('sqlite:////path/to/pysims.db')

        # Exercise
        # ===========================================================
        db = SQLiteDatabase(url=url)

        # Verify
        # ===========================================================
        assert db.url == url, 'url attribute is incorrect!'
        assert db.path == SQLITE_DEFAULT_DB_FILE_PATH, 'path attribute is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        'path',
        (
            pytest.param('/does/not/exist/pysims.db', id='str'),
            pytest.param(Path('/does/not/exist/pysims.db'), id='Path'),
        ),
    )
    @pytest.mark.raises
    def test_path_does_not_exist(self, path: str | Path) -> None:
        r"""Supply a database path that does not exist.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            SQLiteDatabase(path=path)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert str(path) in exc_info_str, 'path not in error message!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_path_is_dir(self) -> None:
        r"""Supply a database path that points to a directory.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        path = Path.cwd()

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            SQLiteDatabase(path=path)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert str(path) in exc_info_str, 'path not in error message!'

        # Clean up - None
        # ===========================================================

    def test_available_database_registration(self) -> None:
        r"""Test that `SQLiteDatabase` is a member of the available database registry.

        `SQLiteDatabase` is registered upon creation by the `__init_subclass__` method.
        """

        # Setup - None
        # ===========================================================

        # Exercise - None
        # ===========================================================

        # Verify
        # ===========================================================
        assert available_databases[SQLiteDatabase.name] is SQLiteDatabase

        # Clean up - None
        # ===========================================================


@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
class TestDatabaseSection:
    r"""Tests for the config model `DatabaseSection`.

    The `DatabaseSection` class defines the database section in the configuration.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `DatabaseSection`."""

        # Setup
        # ===========================================================
        backend = 'sqlite'
        schema = 'my_schema'
        prefix = 'prefix'

        # Exercise
        # ===========================================================
        db = DatabaseSection(backend='SQLite', schema=schema, prefix=prefix)

        # Verify
        # ===========================================================
        assert db.backend == backend
        assert db.db_schema == schema
        assert db.prefix == prefix
        assert db.sqlite.dict() == SQLiteDatabase().dict()

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_backend(self) -> None:
        r"""Test to supply an invalid backend to `DatabaseSection`.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        backend = 'SQLarge'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            DatabaseSection(backend=backend)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert backend in exc_info_str, 'backend not in error message!'

        # Clean up - None
        # ===========================================================


class TestNetmoreSensorPortal:
    r"""Tests for the config model `NetmoreSensorPortal`.

    The `NetmoreSensorPortal` class defines the configuration for the Netmore sensor portal.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `NetmoreSensorPortal`."""

        # Setup
        # ===========================================================
        data = {
            'username': 'rev',
            'password': 'WarmnessOnTheSoul',
            'base_url': 'https://api.ax7.com',
            'sensor_id_column': 'drums',
        }

        # Exercise
        # ===========================================================
        db = NetmoreSensorPortal.parse_obj(data)

        # Verify
        # ===========================================================
        assert db.dict() == data

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_base_url(self) -> None:
        r"""Test to supply an invalid base url to `NetmoreSensorPortal`.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        base_url = 'https:://api.ax7.com'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            NetmoreSensorPortal(base_url=base_url)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert 'base_url' in exc_info_str, 'base_url not in error message!'

        # Clean up - None
        # ===========================================================

    def test_available_sensor_portal_registration(self) -> None:
        r"""Test that `NetmoreSensorPortal` is a member of the available sensor portal registry.

        `NetmoreSensorPortal` is registered upon creation by the `__init_subclass__` method.
        """

        # Setup - None
        # ===========================================================

        # Exercise - None
        # ===========================================================

        # Verify
        # ===========================================================
        assert available_sensor_portals[NetmoreSensorPortal.name] is NetmoreSensorPortal

        # Clean up - None
        # ===========================================================


class TestSensorPortalSection:
    r"""Tests for the config model `SensorPortalSection`.

    The `SensorPortalSection` class defines portal section in configuration.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `SensorPortalSection`."""

        # Setup
        # ===========================================================
        portal = 'netmore'

        # Exercise
        # ===========================================================
        p = SensorPortalSection(portal=portal)

        # Verify
        # ===========================================================
        assert p.portal == portal, 'portal key is incorrect!'
        assert p.netmore.dict() == NetmoreSensorPortal().dict(), 'netmore key is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_portal(self) -> None:
        r"""Test to supply an invalid value to the `portal` attribute.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        portal = 'Avenged Sevenfold'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            SensorPortalSection(portal=portal)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert portal in exc_info_str, 'portal not in error message!'

        # Clean up - None
        # ===========================================================


class TestExportSection:
    r"""Tests for the config model `ExportSection`.

    The `ExportSection` class defines the export section in the configuration.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `ExportSection`."""

        # Setup
        # ===========================================================
        _format = 'CSV'
        format_exp = 'csv'
        creation_datetime = False
        creation_datetime_format = r'%y-%m-%d'
        output_dir = Path.cwd()

        # Exercise
        # ===========================================================
        e = ExportSection(
            format=_format,
            creation_datetime=creation_datetime,
            creation_datetime_format=creation_datetime_format,
        )

        # Verify
        # ===========================================================
        assert e.format == format_exp, 'format key is incorrect!'
        assert e.creation_datetime == creation_datetime, 'creation_datetime key is incorrect!'
        assert (
            e.creation_datetime_format == creation_datetime_format
        ), 'creation_datetime_format key is incorrect!'
        assert e.output_dir == output_dir, 'output_dir key is incorrect!'
        assert e.csv.dict() == CsvFileFormat().dict(), 'csv key is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_format(self) -> None:
        r"""Test to supply an invalid export format.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        _format = 'City of Evil'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            ExportSection(format=_format)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert _format in exc_info_str, 'format not in error message!'

        # Clean up - None
        # ===========================================================


class TestLogHandler:
    r"""Tests for the config model `LogHandler`.

    The `LogHandler` is the base class for a log handler.
    """

    @pytest.mark.parametrize(
        'min_log_level, min_log_level_exp',
        (
            pytest.param(LogLevels.WARNING, LogLevels.WARNING, id='LogLevels.WARNING'),
            pytest.param(10, LogLevels.DEBUG, id='int=10'),
        ),
    )
    def test_init_with_min_log_level(
        self, min_log_level: LogLevels | int, min_log_level_exp: LogLevels
    ) -> None:
        r"""Test to create an instance of `LogHandler` with different values for `min_log_level`."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        lh = LogHandler(min_log_level=min_log_level)  # type: ignore

        # Verify
        # ===========================================================
        assert lh.min_log_level == min_log_level_exp

        # Clean up - None
        # ===========================================================


class TestStreamLogHandler:
    r"""Tests for the config model `StreamLogHandler`.

    The `StreamLogHandler` class defines the configuration for the stream log handler.
    """

    @pytest.mark.parametrize(
        'streams, streams_exp',
        (
            pytest.param(
                [Streams.STDIN, Streams.STDOUT, Streams.STDERR],
                (Streams.STDIN, Streams.STDOUT, Streams.STDERR),
                id='list[Streams]',
            ),
            pytest.param(
                ['stdout', 'stderr'],
                (Streams.STDOUT, Streams.STDERR),
                id='list[str]',
            ),
            pytest.param((Streams.STDOUT,), (Streams.STDOUT,), id='tuple[Streams]'),
            pytest.param(
                {Streams.STDIN, Streams.STDOUT, Streams.STDERR},
                (Streams.STDIN, Streams.STDOUT, Streams.STDERR),
                id='set[Streams]',
            ),
            pytest.param(
                [Streams.STDERR, Streams.STDOUT, Streams.STDOUT],
                (Streams.STDERR, Streams.STDOUT),
                id='list[Streams] with duplicate',
            ),
        ),
    )
    def test_init(
        self,
        streams: list[Streams] | list[str] | tuple[Streams] | set[str],
        streams_exp: tuple[Streams],
    ) -> None:
        r"""Test to create an instance of `StreamLogHandler`."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        sh = StreamLogHandler(streams=streams)  # type: ignore

        # Verify
        # ===========================================================
        for stream in streams_exp:
            assert stream in sh.streams, f'{stream=} not in StreamLogHandler.streams!'

        # Clean up - None
        # ===========================================================


class TestFileLogHandler:
    r"""Tests for the config model `FileLogHandler`.

    The `FileLogHandler` class defines the configuration for the file log handler.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `FileLogHandler`."""

        # Setup
        # ===========================================================
        path = Path.cwd() / 'pysims.log'
        username_in_filename = True

        # Exercise
        # ===========================================================
        sh = FileLogHandler(path=path, username_in_filename=username_in_filename)

        # Verify
        # ===========================================================
        assert sh.path == path, 'key "path" is incorrect!'
        assert (
            sh.username_in_filename == username_in_filename
        ), 'key "username_in_filename" is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_log_file_path(self) -> None:
        r"""Test to supply a directory instead of a file to the `path` attribute.

        `exceptions.ConfigError` is expected to be raised.
        """

        # Setup
        # ===========================================================
        path = Path.cwd()

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            FileLogHandler(path=path)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert 'path' in exc_info_str, 'path not in error message!'

        # Clean up - None
        # ===========================================================


class TestLoggingSection:
    r"""Tests for the config model `LoggingSection`.

    The `LoggingSection` class defines the logging section in the configuration.
    """

    def test_init(self) -> None:
        r"""Test to create an instance of `LoggingSection`."""

        # Setup
        # ===========================================================
        disabled = True
        min_log_level = LogLevels.CRITICAL
        _format = 'some format'
        datetime_format = r'%y-%m-%d'

        # Exercise
        # ===========================================================
        l = LoggingSection(
            disabled=disabled,
            min_log_level=min_log_level,
            format=_format,
            datetime_format=datetime_format,
        )

        # Verify
        # ===========================================================
        assert l.disabled == disabled, 'disabled key is incorrect!'
        assert l.min_log_level == min_log_level, 'min_log_level key is incorrect!'
        assert l.format == _format, 'format key is incorrect!'
        assert l.datetime_format == datetime_format, 'datetime_format key is incorrect!'
        assert l.stream.dict() == StreamLogHandler().dict(), 'stream key is incorrect!'
        assert l.file.dict() == FileLogHandler().dict(), 'file key is incorrect!'

        # Clean up - None
        # ===========================================================


class TestInitConfigManager:
    r"""Tests for initializing the config model `ConfigManager`.

    The `ConfigManager` handles the program's configuration.
    """

    @pytest.mark.usefixtures('mocked_system_username_env_var')
    def test_default_config(self, default_config: dict[str, Any]) -> None:
        r"""Test to create an instance of `ConfigManager` with all default values.

        The config values not specified should be filled in with the default values.
        """

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        cm = ConfigManager()

        # Verify
        # ===========================================================
        assert cm.dict(by_alias=True) == default_config

        # Clean up - None
        # ===========================================================

    def test_load_editor_user_api_key_database_sqlite_url_from_env_var_override_init_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""Test to load config keys from environment variables.

        The config keys `editor`, `user.api_key` and `database.sqlite.url` are loaded from
        environment variables and they should override the values passed to the initializer
        of `ConfigManager`.
        """

        # Setup
        # ===========================================================
        data = {
            'editor': 'emacs',
            'user': {'api_key': 'waking_the_fallen'},
            'database': {'sqlite': {'url': 'sqlite://'}},
        }
        prefix = 'pysims_'
        editor = 'code'
        api_key = 'city_of_evil'
        url = 'sqlite:///a7x.sqlite'

        monkeypatch.setenv(name=f'{prefix}editor', value=editor)
        monkeypatch.setenv(name=f'{prefix}user__api_key', value=api_key)
        monkeypatch.setenv(name=f'{prefix}DATABASE__SQLITE__URL', value=url)

        # Exercise
        # ===========================================================
        cm = ConfigManager.parse_obj(data)

        # Verify
        # ===========================================================
        assert cm.editor == editor, 'editor key is incorrect!'
        assert cm.user.api_key == api_key, 'user.api_key key is incorrect'
        assert cm.database.sqlite.url == make_url(url), 'database.sqlite.url key is incorrect'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_sqlite_db_path_and_portal(self) -> None:
        r"""Test to parse a configuration with invalid values.

        The keys `database.sqlite.path` and `portal.portal` contain invalid values.
        `exceptions.ConfigError` is expected to be raised and the validation should
        stop at the first found error (`database.sqlite.path`). Only error info about
        `database.sqlite.path` should appear in the error message.
        """

        # Setup
        # ===========================================================
        path = '/does/not/exist'
        portal = 'A Little Piece of Heaven'
        data = {
            'editor': 'vim',
            'database': {'sqlite': {'path': path}},
            'portal': {'portal': portal},
        }

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            ConfigManager.parse_obj(data)

        # Verify
        # ===========================================================
        exc_info_str = exc_info.exconly()
        print(exc_info_str)

        assert path in exc_info_str, 'database.sqlite.path not in error message!'
        assert portal not in exc_info_str, 'portal.portal in error message!'

        # Clean up - None
        # ===========================================================

    def test_extra_keys_ignored(self) -> None:
        r"""Test to provide extra config keys not part of the defined configuration.

        The extra keys should be ignored by the validation and not set on `ConfigManager`.
        """

        # Setup
        # ===========================================================
        data = {'unknown_key': 'test', 'editor': 'emacs', 'database': {'unknown_key_2': 'test_2'}}

        # Exercise
        # ===========================================================
        cm = ConfigManager.parse_obj(data)

        # Verify
        # ===========================================================
        assert not hasattr(cm, 'unknown_section'), 'Key "unknown_section" found on cm!'
        assert not hasattr(
            cm.database, 'unknown_section_key_2'
        ), 'Key "unknown_section_2" found on cm.database!'

        # Clean up - None
        # ===========================================================
