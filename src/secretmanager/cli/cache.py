import typer

from secretmanager.secret import CACHE

app = typer.Typer(name="cache", pretty_exceptions_enable=False)


@app.command()
def reset():
    """
    Get secret from manager
    """
    CACHE.clear()
