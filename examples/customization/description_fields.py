from argdantic import ArgField, ArgParser

cli = ArgParser()


@cli.command()
def hello(
    name: str = ArgField("-n", default="John", description="Your name"),
    age: int = ArgField("-a", default=30, description="Your age"),
):
    """Print a greeting message."""
    print(f"Hello, {name}!")
    print(f"You are {age} years old.")


if __name__ == "__main__":
    cli()
