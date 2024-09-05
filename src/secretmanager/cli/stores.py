import typer
from rich.console import Console
from rich.table import Table

from secretmanager.registry import _known_implementations, registry

app = typer.Typer(name="stores", pretty_exceptions_enable=False)
console = Console()


@app.command("list")
def store_list(available_only: bool = False):
    """List available stores"""
    table = Table("Store name", "Available", "Dependency")
    for k, v in _known_implementations.items():
        table.add_row(k, format(k in registry), v["dependency"])

    console.print(table)
