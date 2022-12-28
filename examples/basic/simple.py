from argdantic import ArgParser

cli = ArgParser()


@cli.command()
def hello(name: str):
    print(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
