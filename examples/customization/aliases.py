from argdantic import ArgField, ArgParser

cli = ArgParser()


@cli.command()
def hello(name: str = ArgField("-n"), age: int = ArgField("-a")):
    """Print a greeting message."""
    print(f"Hello, {name}!")
    print(f"You are {age} years old.")


if __name__ == "__main__":
    cli()
