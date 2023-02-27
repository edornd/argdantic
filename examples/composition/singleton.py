from pydantic import BaseModel

from argdantic import ArgParser


class Image(BaseModel):
    name: str


class Item(BaseModel):
    name: str
    description: str
    image: Image = None


cli = ArgParser()


@cli.command(singleton=True)
def create_item(item: Item):
    print(item)


if __name__ == "__main__":
    cli()
