# Argdantic

*Typed command line interfaces, powered by [argparse](https://docs.python.org/3/library/argparse.html) and [pydantic](https://github.com/pydantic/pydantic).*


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

## Acknowledgements

This project is heavily inspired by other awesome works, including:

- [click](https://github.com/pallets/click): the most popular CLI library for Python for complex applications, the best alternative to `argparse`.

- [typer](https://github.com/tiangolo/typer): based on `click`, a great project that inspired the creation of `argdantic`. It is a great alternative, however it does not support `pydantic` models at the moment.

- [pydantic-cli](https://github.com/mpkocher/pydantic-cli): a mature project that provides a similar experience to `argdantic`, however it does not support nested models, commands and different sources.

Do you like `argdantic`, but prefer `click` as a CLI library? Check out [clidantic](https://github.com/edornd/clidantic), a twin project that uses `click` instead of `argparse`.

## License

This project is licensed under the terms of the MIT license.

## Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.
