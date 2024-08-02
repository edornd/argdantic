from datetime import date
from typing import List

from pydantic import BaseModel

from argdantic import ArgParser


class Image(BaseModel):
    name: str


class Item(BaseModel):
    name: str
    description: str
    image: Image | None = None
    dates: List[date]


cli = ArgParser()


@cli.command(singleton=True)
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
