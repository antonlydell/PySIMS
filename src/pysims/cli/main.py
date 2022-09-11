r"""The main module of the CLI containing the entry point to start the program."""

# Standard library
import logging

# Third-party
import click

# Local
from pysims import __releasedate__

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
@click.version_option(message=f'%(prog)s, version: %(version)s, release date: {__releasedate__}')
def main(ctx: click.Context):
    r"""Python Sensor Integration Management System (PySIMS)

    Manage and integrate IoT sensors with meter data management systems (MDMs).
    Fetch and decode sensor meter data from a sensor portal and export it in various formats.
    """


if __name__ == '__main__':
    main()
