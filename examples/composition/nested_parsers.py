from argdantic import ArgParser

users = ArgParser(name="users")
books = ArgParser(name="books")


@users.command()
def add_user(name: str, age: int):
    """Adds a single user."""
    print(f"Adding user: {name} ({age})")


@users.command()
def delete_user(name: str):
    """Deletes a user by name."""
    print(f"Deleting user: {name}")


@books.command()
def add_book(name: str, author: str):
    """Adds a book, with name and author."""
    print(f"Adding book: {name} ({author})")


@books.command()
def delete_book(name: str):
    """Deletes a book by name."""
    print(f"Deleting book: {name}")


cli = ArgParser()
cli.add_parser(users)
cli.add_parser(books)

if __name__ == "__main__":
    cli()
