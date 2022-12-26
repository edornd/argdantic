from typing import Set

from pydantic import BaseModel

from argdantic import ArgParser


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


@cli.command()
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
