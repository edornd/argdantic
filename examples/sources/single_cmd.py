from typing import Set

from pydantic import BaseModel

from argdantic import ArgParser
from argdantic.sources import (
    EnvSettingsSource,
    JsonSettingsSource,
    TomlSettingsSource,
    YamlSettingsSource,
)


class Image(BaseModel):
    url: str
    name: str


class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tags: Set[str] = set()
    image: Image = None


cli = ArgParser()


@cli.command(
    sources=[
        EnvSettingsSource(env_file=".env"),
        JsonSettingsSource(json_file="settings.json"),
        YamlSettingsSource(yaml_file="settings.yaml"),
        TomlSettingsSource(toml_file="settings.toml"),
    ]
)
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
