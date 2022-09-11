r"""PySIMS (Python Sensor Integration Management System)

PySIMS is a CLI for managing and integrating IoT sensors with meter data management systems (MDMs).
Fetch and decode sensor meter data from a sensor portal and export it in various formats.
"""

from datetime import date


__versiontuple__: tuple[int | str, ...] = (0, 0, 1)
r"""The version of PySIMS in a comparable form.
Adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_
(MAJOR.MINOR.PATCH).
"""

__version__ = "0.0.1"
r"""The PySIMS version string."""

__releasedate__: date = date(2022, 9, 11)
r"""The release date of the version specified in :data:`__versiontuple__`."""
