from argdantic import ArgParser

cli = ArgParser(force_group=True)


@cli.command(name="greetings")
def hello(name: str):
    """
    Say hello.
    """
    print(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
