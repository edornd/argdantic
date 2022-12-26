from argdantic import ArgParser

cli = ArgParser()


@cli.command()
def status(name: str, age: int, weight: float, data: bytes, flag: bool):
    print(f"name: {name}")
    print(f"age: {age}")
    print(f"weight: {weight}")
    print(f"data: {data}")
    print(f"flag: {flag}")


if __name__ == "__main__":
    cli()
