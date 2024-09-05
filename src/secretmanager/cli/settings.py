import json
from enum import Enum
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel, JsonValue
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from termcolor import colored

from secretmanager.settings import Settings

app = typer.Typer(name="settings", pretty_exceptions_enable=False)


class FormatChoice(str, Enum):
    PLAIN = "plain"
    JSON = "json"
    YAML = "yaml"


def _plain_print(obj: BaseModel, exclude_unset: bool = False):
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
            is_default = format(default) == value
            if not (exclude_unset and is_default):
                yield {
                    "ENVIRONMENT VARIABLE": key.upper(),
                    "VALUE": value,
                    "TYPE": getattr(field.annotation, "__name__", str(field.annotation)),
                    "DEFAULT": format(default),
                    "DESCRIPTION": description,
                }

    elems = list(get_elements(obj, key="SM"))
    cols = ["ENVIRONMENT VARIABLE", "VALUE", "DEFAULT", "TYPE", "DESCRIPTION"]
    max_lengths = []
    for c in cols:
        n = max(len(format(e[c])) for e in elems) if elems else 0
        max_lengths.append(max(n, len(c)))
    spacing = (len(cols) - 1) * 3
    print(" | ".join([f"{col: <{leng}}" for col, leng in zip(cols, max_lengths)]))
    print(f"{'' :-<{sum(max_lengths) + spacing}}")
    for elem in elems:
        print(
            colored(
                " | ".join(f"{elem[col]: <{leng}}" for col, leng in zip(cols, max_lengths)),
                color=None if elem["VALUE"] == elem["DEFAULT"] else "red",
            )
        )


@app.command()
def view(
    format: Annotated[FormatChoice, typer.Option()] = FormatChoice.PLAIN,
    pretty: Annotated[bool, typer.Option] = True,
    exclude_unset: Annotated[bool, typer.Option] = False,
):
    """View settings"""
    if format == FormatChoice.PLAIN:
        _plain_print(Settings, exclude_unset)
    elif format == FormatChoice.JSON:
        indent = 2 if pretty else None
        print(json.dumps(Settings.model_dump(exclude_unset=exclude_unset), indent=indent))
    elif format == FormatChoice.YAML:
        indent = 2 if pretty else None
        print(yaml.dump(Settings.model_dump(exclude_unset=exclude_unset), indent=indent, sort_keys=False))
