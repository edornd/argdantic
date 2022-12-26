from argdantic import ArgParser

cli = ArgParser()


@cli.command()
def hello(name: str = "World", age: int = 42):
    """Print a greeting message."""
    print(f"Hello, {name}!")
    print(f"You are {age} years old.")


if __name__ == "__main__":
    cli()
