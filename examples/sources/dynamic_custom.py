from pathlib import Path

from pydantic import BaseModel

from argdantic import ArgParser
from argdantic.sources import YamlFileLoader, from_file


@from_file(loader=YamlFileLoader, use_field="path")
class Optimizer(BaseModel):
    path: Path
    name: str = "SGD"
    learning_rate: float = 0.01
    momentum: float = 0.9


@from_file(loader=YamlFileLoader, required=False)
class Dataset(BaseModel):
    name: str = "CIFAR10"
    batch_size: int = 32
    tile_size: int = 256
    shuffle: bool = True


cli = ArgParser()


@cli.command()
def create_item(optim: Optimizer, dataset: Dataset = Dataset()):
    print(dataset)
    print(optim)


if __name__ == "__main__":
    cli()
