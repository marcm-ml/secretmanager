import json
from enum import Enum
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel, JsonValue
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from rich import print
from rich.console import Console
from rich.table import Table

from secretmanager.settings import Settings

app = typer.Typer(name="settings", pretty_exceptions_enable=False)
console = Console()


class FormatChoice(str, Enum):
    PLAIN = "plain"
    JSON = "json"
    YAML = "yaml"


def get_elements(obj: BaseModel | JsonValue, key: str, field: FieldInfo | None = None, is_nested: bool = False):
    if isinstance(obj, BaseModel):
        for k, f in obj.model_fields.items():
            _key = key + "__" + k if is_nested else key + "_" + k
            value: BaseModel | JsonValue = getattr(obj, k)
            yield from get_elements(value, key=_key, field=f, is_nested=isinstance(value, BaseModel))
    elif field is not None:
        value = format(obj) if format(obj) else '""'
        default = ""
        if field.default is not PydanticUndefined:
            default = format(field.default) if format(field.default) else '""'
        elif field.default_factory:
            _default = field.default_factory()
            default = format(_default) if format(_default) else '""'
        description = field.description or ""
        yield {
            "ENVIRONMENT VARIABLE": key.upper(),
            "VALUE": value,
            "TYPE": getattr(field.annotation, "__name__", str(field.annotation)),
            "DEFAULT": format(default),
            "DESCRIPTION": description,
        }


@app.command("list")
def setting_list(
    format_style: Annotated[FormatChoice, typer.Option("--format")] = FormatChoice.PLAIN,
    pretty: Annotated[bool, typer.Option] = True,
    exclude_unset: Annotated[bool, typer.Option] = False,
):
    """View settings"""
    if format_style == FormatChoice.PLAIN:
        elems = list(get_elements(Settings, key="SM"))
        cols = ["ENVIRONMENT VARIABLE", "VALUE", "DEFAULT", "TYPE", "DESCRIPTION"]
        table = Table("Environment Variable", "Value", "Default", "Type", "Description")
        for elem in elems:
            if exclude_unset and elem["VALUE"] == format(elem["DEFAULT"]):
                continue
            table.add_row(*[format(elem[c]) for c in cols])
        console.print(table)
    elif format_style == FormatChoice.JSON:
        indent = 2 if pretty else None
        print(json.dumps(Settings.model_dump(exclude_unset=exclude_unset), indent=indent))
    elif format_style == FormatChoice.YAML:
        indent = 2 if pretty else None
        print(yaml.dump(Settings.model_dump(exclude_unset=exclude_unset), indent=indent, sort_keys=False))
