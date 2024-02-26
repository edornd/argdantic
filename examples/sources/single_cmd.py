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
    url: str = None
    name: str = None


class Item(BaseModel):
    name: str = "test"
    description: str = None
    price: float = 10.0
    tags: Set[str] = set()
    image: Image = None


cli = ArgParser()


@cli.command(
    sources=[
        EnvSettingsSource(env_file=".env"),
        JsonSettingsSource(path="settings.json"),
        YamlSettingsSource(path="settings.yaml"),
        TomlSettingsSource(path="settings.toml"),
    ]
)
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
