from argdantic import ArgParser
from argdantic.sources import YamlModel


class Optimizer(YamlModel):
    name: str = "SGD"
    learning_rate: float = 0.01
    momentum: float = 0.9


class Dataset(YamlModel):
    name: str = "CIFAR10"
    batch_size: int = 32
    tile_size: int = 256
    shuffle: bool = True


cli = ArgParser()


@cli.command()
def create_item(dataset: Dataset, optim: Optimizer):
    print(dataset)
    print(optim)


if __name__ == "__main__":
    cli()
