from argdantic import ArgParser

cli = ArgParser()


@cli.command()
def hello_world():
    print("Hello World!")


if __name__ == "__main__":
    cli()
