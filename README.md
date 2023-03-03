# argdantic
Typed command line interfaces with [`argparse`](https://docs.python.org/3/library/argparse.html) and [`pydantic`](https://github.com/pydantic/pydantic).

[![test passing](https://img.shields.io/github/actions/workflow/status/edornd/argdantic/test.yml?branch=main)](https://github.com/edornd/argdantic)
[![coverage](https://img.shields.io/codecov/c/gh/edornd/argdantic)](https://codecov.io/gh/edornd/argdantic)
[![pypi version](https://img.shields.io/pypi/v/argdantic)](https://pypi.org/project/argdantic/)
[![python versions](https://img.shields.io/pypi/pyversions/argdantic)](https://github.com/edornd/argdantic)

[![license](https://img.shields.io/github/license/edornd/argdantic)](https://github.com/edornd/argdantic)
[![documentation](https://img.shields.io/badge/documentation-%F0%9F%93%9A-blue)](https://edornd.github.io/argdantic/)
---

## Features

`argdantic` provides a thin boilerplate layer to provide a modern CLI experience, including:
- **Typed arguments:** arguments require full typing by default, enforcing clarity and help your editor provide better support (linting, hinting).
- **Nested models:** exploit `pydantic` models to scale from simple primitives to complex nested configurations with little effort.
- **Nested commands:** combine commands and build complex hierarchies to build complex interfaces.
- **Validation by default:** thanks to `pydantic`, field validation is provided by default, with the desired complexity.
- **Multiple sources:** arguments can be provided from multiple sources, including environment variables, JSON, TOML and YAML files.

## Quickstart

### Installation
Installing `argdantic` can be done from source, or simply using `pip`.
The only required dependency is, of course, *pydantic*, while the remaining can be selected depending on your needs:

```console
recommended choice: install everything
this includes orjson, pyyaml, tomli, python-dotenv
user@pc:~$ pip install argdantic[all]

env, json, toml or yaml dependencies
user@pc:~$ pip install argdantic[env|json|toml|yaml]

minimum requirement, only pydantic included
user@pc:~$ pip install argdantic
```

### A Simple Example

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

### Using Models

Plain arguments and `pydantic` models can be mixed together:

```python
from argdantic import ArgParser
from pydantic import BaseModel

parser = ArgParser()


class Item(BaseModel):
    name: str
    price: float


@parser.command()
def buy(item: Item, quantity: int):
    print(f"Bought {quantity} X {item.name} at ${item.price:.2f}.")

if __name__ == "__main__":
    parser()
```

This will produce the following help:

```console
usage: cli.py [-h] --item.name TEXT --item.price FLOAT --quantity INT

optional arguments:
  -h, --help          show this help message and exit
  --item.name TEXT
  --item.price FLOAT
  --quantity INT
```

### Arguments From Different Sources

`argdantic` supports several inputs:
- **`.env` files**, environment variables, and secrets thanks to *pydantic*.
- **JSON files**, using either the standard `json` library, or `orjson` if available.
- **YAML files**, using the `pyyaml` library.
- **TOML files**, using the lightweight `tomli` library.

Sources can be imported and added to each command independently, as such:

```python
from argdantic import ArgParser
from argdantic.sources import EnvSettingsSource, JsonSettingsSource

parser = ArgParser()


@parser.command(
    sources=[
        EnvSettingsSource(env_file=".env", env_file_encoding="utf-8"),
        JsonSettingsSource(path="settings.json"),
    ]
)
def sell(item: str, quantity: int, value: float):
    print(f"Selling: {item} x {quantity}, {value:.2f}$")


if __name__ == "__main__":
    parser()
```

This is just a brief introduction to the library, more examples and details can be found in the [documentation](https://edornd.github.io/argdantic/).

## Contributing

Contributions are welcome! You can open a new issue to report bugs, or suggest new features. If you're brave enough, pull requests are also welcome.
