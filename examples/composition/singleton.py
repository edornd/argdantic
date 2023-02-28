from typing import List
from datetime import date
from pydantic import BaseModel

from argdantic import ArgParser


class Test(BaseModel):
    test: List[date]

class Image(BaseModel):
    name: str


class Item(BaseModel):
    name: str
    description: str
    image: Image = None
    test: Test


cli = ArgParser()


@cli.command(singleton=True)
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
