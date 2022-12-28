from argdantic import ArgParser

cli = ArgParser(force_group=True)


@cli.command()
def hello(name: str):
    """Print a greeting message."""
    print(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
