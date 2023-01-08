# Introduction

## Parsers

The main building block of *argdantic* is represented by a `ArgParser` instance.
Every CLI requires at least one active parser, which serves as main entry point.
A parser simply acts as a collection of commands, which are only executed upon call.

Any parser must first be imported, instantiated, then called in a main, like so:

```python title="main.py" linenums="1" hl_lines="1 3 7"
{!examples/basic/empty.py!}
```
However, **this code is not enough to have a working CLI**. If you attempt to run it you will obtain:
```console
$ python main.py
> AssertionError: Parser must have at least one command or group of commands
```
This is the expected behavior, as a parser without any command is useless: check the [Commands](#commands) section for more information.

## Commands

Commands are the backbone of any parser. Underneath, they are simply functions that are called when requested by the user.
A command can be added to a parser by using the `@parser.command()` decorator, like so:

```python title="main.py" linenums="1" hl_lines="6"
{!examples/basic/empty_cmd.py!}
```

When executed, the script will provide the following output:
```console
$ python main.py
> Hello World!
```
This is a step forward, however the command is still not very useful. Let's see how to add arguments to it.

## Arguments

Arguments are the way to provide information and dynamic functionality to a command.
They are defined by simply adding them to the command's signature, like so:

```python title="main.py" linenums="1" hl_lines="7"
{!examples/basic/simple.py!}
```

!!! note
    Of course, typing is crucial to ensure that `argdantic` can correctly parse the arguments.
    The framework however will be kind enough to provide an error message if a field does not provide a type annotation.


When executed, the script will provide the following output:
```console
$ python main.py
> usage: main.py [-h] --name TEXT
> main.py: error: the following arguments are required: --name
```
This is correct, as the `--name` argument is required. Let's see how to provide it.

```console
$ python main.py --name John
> Hello, John!
```

## Help Messages

Of course, randomly executing a command without any information is not very useful.
The `--help` argument is automatically added to every command, and provides a summary of the command's arguments.
For instance, running the help command on the previous example will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] --name TEXT
>
> optional arguments:
>  -h, --help   show this help message and exit
>  --name TEXT  (required)
```

You may have noticed two things: if you are familiar with `argparse`, you probably already know that
the `--help` argument is automatically added to every command. In addition, `argdantic` explicitly
provides the `(required)` tag to every argument that does not specify a default value.
This is done to ensure that the user is aware of some missing options, even before the command is executed.
