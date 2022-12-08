# argdantic
Typed command line interfaces with `argparse` and [`pydantic`](https://github.com/pydantic/pydantic).

[![test passing](https://img.shields.io/github/workflow/status/edornd/argdantic/test/main)](https://github.com/edornd/argdantic)
[![coverage](https://img.shields.io/codecov/c/gh/edornd/argdantic)](https://codecov.io/gh/edornd/argdantic)
[![pypi version](https://img.shields.io/pypi/v/argdantic)](https://pypi.org/project/argdantic/)
[![python versions](https://img.shields.io/pypi/pyversions/argdantic)](https://github.com/edornd/argdantic)
---

## Features

`argdantic` provides a thin boilerplate layer to provide a modern CLI experience, including:
- **Typed arguments:** arguments require full typing by default, enforcing clarity and help your editor provide better support (linting, hinting).
- **Nested models:** exploit `pydantic` models to scale from simple primitives to complex nested configurations with little effort.
- **Nested commands:** combine commands and build complex hierarchies to build complex interfaces.
- **Validation by default:** thanks to `pydantic`, field validation is provided by default, with the desired complexity.

## A Simple Example

Creating a CLI with `argdantic` can be as simple as:
```python
from argdantic import ArgParser

# 1. create a CLI instance
parser = ArgParser()


# 2. decorate the function to be called
@parser.command()
def buy(name: str, quantity: int, price: float):
    print(f"Bought {quantity} {name} at ${price:.2f}.")

# 3. Use your CLI by simply calling it
if __name__ == "__main__":
    parser()
```
Then, in a terminal, the `help` command can provide the usual information:

```console
$ python cli.py --help
> usage: buy [-h] --name TEXT --quantity INT --price FLOAT
>
> optional arguments:
>   -h, --help      show this help message and exit
>   --name TEXT
>   --quantity INT
>   --price FLOAT
```
This gives us the required arguments for the execution:
```console
$ python cli.py --name apples --quantity 10 --price 3.4
> Bought 10 apples at $3.40.
```
