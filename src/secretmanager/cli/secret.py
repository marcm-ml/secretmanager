import typer
from rich import print

from secretmanager.secret import Secret

app = typer.Typer(name="secret", pretty_exceptions_enable=False)


@app.command()
def get(key: str):
    """
    Get secret from manager
    """
    print(Secret(key)())
