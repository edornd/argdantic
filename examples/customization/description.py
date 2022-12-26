from argdantic import ArgParser

cli = ArgParser(force_group=True)


@cli.command(help="Print a greeting message")
def hello(name: str):
    print(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
