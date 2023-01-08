# Customization

Argdantic supports a number of customization options, which can be used to change the default behavior of the CLI.
Being based on `argparse` and `pydantic`, the customization options are limitless, however the most common ones are listed below.

- **Command names:** a custom help message to be displayed when the `--help` flag is passed.
- **Command description:** a custom help message to be displayed when the `--help` flag is passed.
- **Field descriptions:** a custom help message to be displayed when the `--help` flag is passed.
- **Field aliases:** a list of optional names that can be used instead of the field name.
- **Field default values:** a default value to be used when the field is not provided.

The following sections will provide a brief overview of these options, and how to use them.

## Command Names

By default, the name of the function that is decorated with `@parser.command()` is used as the name of the command.
This can be changed by passing a `name` argument to the decorator:

```python title="main.py" linenums="1" hl_lines="6"
{!examples/customization/custom_name.py!}
```

When executed, the script will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] --name TEXT
>
> optional arguments:
>  -h, --help   show this help message and exit
>  --name TEXT  (required)
```

**Wait a minute, where is the custom name?**

By default, with only one command, the name of the command is not displayed, nor used to execute the command.
This can be changed by:

1. Registering more than one command, the easiest option.
2. By passing the `force_group` argument to the parser.

### Multiple Commands

When more than one command is registered, its name is required to execute that specific CLI function.
For instance, the following script:

```python title="main.py" linenums="1" hl_lines="6 14"
{!examples/customization/custom_name_multi.py!}
```

When executed, the script will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] <command> ...
>
> positional arguments:
>   <command>
>     hi        Say hello.
>     bye       Say goodbye.
>
> optional arguments:
>   -h, --help  show this help message and exit
```

The `hi` and `bye` commands are now available, and can be executed by passing their name as the first argument:

```console
$ python main.py hi --name John
> Hello, John!
```

You also probably noticed that the commands also provide a description.
This can be customized in many ways, and will be covered in the next section.

### Forced Groups

The `force_group` argument can be used to force the creation of a group, even if only one command is registered.
This can be useful if you want to force users to provide the command name upon execution.

For instance, the following script:

```python title="main.py" linenums="1" hl_lines="6 14"
{!examples/customization/custom_name_grouped.py!}
```

When executed, the script will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] <command> ...
>
> positional arguments:
>   <command>
>     greetings
>               Say hello.
>
> optional arguments:
>   -h, --help  show this help message and exit
```

The `greetings` command is now available, and can be executed by passing its name as the first argument:

```console
$ python main.py greetings --name John
> Hello, John!
```

## Command Descriptions

You may have noticed from the previous example that the commands also provide a description.
Descriptions can be customized in two simple ways:

- Automatically, by simply providing a docstring to the function.

- Manually passing a `help` argument to the `@parser.command()` decorator.

For instance, the following script:

```python title="main.py" linenums="1" hl_lines="6"
{!examples/customization/description.py!}
```
Is equivalent to:

```python title="main.py" linenums="1" hl_lines="8"
{!examples/customization/description_docs.py!}
```

When executed, the scripts will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] <command> ...
>
> positional arguments:
>   <command>
>     hello     Print a greeting message.
>
> optional arguments:
>   -h, --help  show this help message and exit
```

## Default Values

Of course, any good CLI tool should provide the user with a way to provide default values for the fields.
Given that defining a command is as simple as defining a function, introducing default values can also be as simple as
providing a default value to the function arguments. For instance:

```python title="main.py" linenums="1" hl_lines="7"
{!examples/customization/default_values.py!}
```

This can be executed with no arguments without any issues:

```console
$ python main.py
> Hello, World!
> You are 42 years old.
```

The default values are also provided in the help message, so that the user is informed about them:

```console
$ python main.py --help
> usage: main.py [-h] [--name TEXT] [--age INT]
>
> optional arguments:
>   -h, --help   show this help message and exit
>   --name TEXT  (default: World)
>   --age INT    (default: 42)
```

### Default Values and Required Fields

Of course, if a field provides a default value, it is no longer required.
This implies that every field must be assigned in some way, either by providing it beforehand or during execution,
which will respectively add a `default` or `required` flag to the help message.
But, as a famous grand master once said, _there is another_: when the default is `None`, the field is neither
marked as `default` nor `required`, so the help message will not contain any flag.
At the time of writing, this is the only way to provide a true optional field.

```python title="main.py" linenums="1" hl_lines="7"
{!examples/customization/default_values_none.py!}
```

The help message will now look like this:

```console
$ python main.py --help
> usage: main.py [-h] [--name TEXT] [--age INT]
>
> optional arguments:
>   -h, --help   show this help message and exit
>   --name TEXT
>   --age INT
```

These are very simple examples, but they can be extended to any field, including
more complex ones such as `List`, `Dict`, and so on.
There are also a few other ways to provide default values, which will be covered in the next sections.

## Field Options

A CLI cannot be complete without a way to customize the fields.
`argdantic` provides a way to customize the fields through the `ArgField` function, which can be seen
as a light wrapper around _pydantic_'s `Field` with a few changes to make it more suitable for CLI tools.
`ArgField`, on top of the arguments provided by `Field`, provides the following options:

- `names`: A variable list of names to provide aliases for the field. This substitutes the positional default value in _pydantic_.

- `default`: A keyword argument to provide a default value for the field. This is now a _keyword_ argument, mirroring `argparse`.

- `description`: A keyword argument to provide a description for the field. This uses the same functionality of `Field`'s `description`.

### Aliases
A common functionality provided by _argparse_ is the ability to provide aliases for the fields.
This option is made available in `argdantic` by using the `ArgField` modifier to the field.
Optional field names can be provided in the following way:

```python title="main.py" linenums="1" hl_lines="7"
{!examples/customization/aliases.py!}
```

Executing the script with the `--help` flag will provide the following output:

```console
$ python main.py --help
> usage: main.py [-h] --name TEXT --age INT
>
> optional arguments:
>   -h, --help            show this help message and exit
>   --name TEXT, -n TEXT  (required)
>   --age INT, -a INT     (required)
```

The message now shows to the user that the `--name` and `--n` flags are equivalent, as well as the `--age` and `--a` flags.
Let's try to execute the script with the new flags:

```console
$ python main.py -n John -a 42
> Hello, John!
> You are 42 years old.
```

### Default with Fields

Substituting the default value in the function signature with the `ArgField` modifier does not preclude the use
of the default value in the function signature. This is now possible by using the `default` keyword argument:

```python title="main.py" linenums="1" hl_lines="8 9"
{!examples/customization/default_with_fields.py!}
```

As before, the script can be executed without any arguments:

```console
$ python main.py
> Hello, World!
> You are 42 years old.
```

### Descriptions

Last but not least, CLI arguments are usually accompanied by a description.
This can be provided in the same way as the default value, by using the `description` keyword argument:

```python title="main.py" linenums="1" hl_lines="8 9"
{!examples/customization/description_fields.py!}
```

This description will be displayed in the help message:

```console
$ python main.py --help
> usage: main.py [-h] [--name TEXT] [--age INT]
>
> optional arguments:
>   -h, --help            show this help message and exit
>   --name TEXT, -n TEXT  your name (default: John)
>   --age INT, -a INT     your age (default: 30)
```

### Other Options

There are a few other options that can be provided to the `ArgField` modifier, which are not covered in this tutorial,
but can be found in the `pydantic` documentation. These include, just to name a few, validators, constraints, and so on.
In general, every other argument provided to `Field` can be provided to `ArgField` in the same way.
