import logging
from enum import Enum

import typer

from secretmanager.cli.secret import app as secret_app
from secretmanager.cli.settings import app as settings_app
from secretmanager.cli.stores import app as stores_app


class Verbosity(str, Enum):
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARN = "WARN"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


app = typer.Typer(pretty_exceptions_enable=False, context_settings={"max_content_width": 500})
app.add_typer(secret_app)
app.add_typer(settings_app)
app.add_typer(stores_app)


@app.callback()
def main(verbose: bool = False, verbosity: Verbosity = Verbosity.INFO):
    """
    Manage users in the awesome CLI app.
    """
    if verbose:
        logging.basicConfig()
        logger = logging.getLogger(__name__.split(".")[0])
        logger.setLevel(verbosity.value)


if __name__ == "__main__":
    app()
