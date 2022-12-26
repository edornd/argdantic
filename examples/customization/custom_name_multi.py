from argdantic import ArgParser

cli = ArgParser()


@cli.command(name="hi")
def hello(name: str):
    """
    Say hello.
    """
    print(f"Hello, {name}!")


@cli.command(name="bye")
def goodbye(name: str):
    """
    Say goodbye.
    """
    print(f"Goodbye, {name}!")


if __name__ == "__main__":
    cli()
