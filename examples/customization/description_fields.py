from argdantic import ArgField, ArgParser

cli = ArgParser()


@cli.command()
def hello(
    name: str = ArgField("-n", default="John", description="your name"),
    age: int = ArgField("-a", default=30, description="your age"),
):
    """Print a greeting message."""
    print(f"Hello, {name}!")
    print(f"You are {age} years old.")


if __name__ == "__main__":
    cli()
