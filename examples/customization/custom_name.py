from argdantic import ArgParser

cli = ArgParser()


@cli.command(name="greetings")
def hello(name: str):
    print(f"Hello, {name}!")


if __name__ == "__main__":
    cli()
