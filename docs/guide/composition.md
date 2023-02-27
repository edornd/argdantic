# Composition

Exploiting both _pydantic_ and _argparse_ functionality,
`argdantic` allows two types of composition: **nested models** and **nested parsers**.
The first allows to define complex inputs, building a hierarchy of models and submodels.
The second allows to organize your code into a series of commands and subcommands, each with its own set of arguments.

## Nested Models

Strictly speaking, every argument stated in the signature of a `@command` function is wrapped into a _pydantic_ model.
This allows two things: first, it makes it easier and more natural for the user to define input arguments, and second,
it allows to define complex inputs, building a hierarchy of models and submodels, directly exploiting the powerful features of _pydantic_.

For example, let's say we want to define a command that takes an input `Item`, which in turn contains an `Image` model.
We can do this by defining two models, and then using the `Item` model as an argument of the `@command` function:

```python  title="nested_models.py" linenums="1" hl_lines="8-10 18"
{!examples/composition/nested_models.py!}
```

Underneath, `argdantic` will automatically create the following structure:

- A nameless root model, inheriting from `BaseConfig` if any extra feature is enabled, and containing:
    * A field `item`, of type `Item`, which defines:
        * A field `name`, of type `str`,
        * A field `description`, of type `str`,
        * A field `price`, of type `float`,
        * A field `tags`, of type `Set[str]`,
        * A field `image`, of type `Image`, which defines:
            * A field `url`, of type `str`,
            * A field `name`, of type `str`

The resulting command line interface, with the help message, will be the following:

```console
$ python nested_models.py --help
> usage: nested_models.py [-h] --item.name TEXT --item.description TEXT --item.price FLOAT --item.tags TEXT [TEXT ...] --item.image.url TEXT --item.image.name TEXT
>
> optional arguments:
>   -h, --help            show this help message and exit
>   --item.name TEXT                (required)
>   --item.description TEXT
>   --item.price FLOAT              (required)
>   --item.tags [TEXT [TEXT ...]]   (default: set())
>   --item.image.url TEXT           (required)
>   --item.image.name TEXT          (required)
```

!!! note

        This argument wrapping behaviour is automated by default to make the command definition as natural as possible,
        however it is possible to define a custom root model by using the `sigleton` keyword argument
        of the `@command` decorator (See, [] )

Executing the command with the required arguments will result in the following output:

```console
$ python nested_models.py --item.name "My Item" \
    --item.description "My Item Description" \
    --item.price 10.0 \
    --item.tags "tag1" "tag2" \
    --item.image.url "https://example.com/image.png" \
    --item.image.name "My Image"
> name='My Item' description='My Item Description' price=10.0 tags={'tag1', 'tag2'} image=Image(url='https://example.com/image.png' name='My Image')
```

!!! note

    Despite that the `Image` model defaults to `None`, you will notice that its fields are still required.
    Strictly speaking, that's the correct behavior, since these fields are not optional. This would have also happened
    if the `image` field had an explicit `Image()` default value.

This is a very simple example, but it shows how to define complex inputs, and how to exploit the power of _pydantic_ to define
a hierarchy of models. In fact, you can define as many levels of nesting as you want, building a complex configuration
that can be easily validated and parsed.
Nested configurations are also supported using different input sources, such as environment variables and configuration files:
see the [Input Sources](../sources) section for more details.

### Singleton Configurations

Sometimes it may be useful to define a single configuration object manually, and then use it as the main
input argument of a command. For instance, imagine a machine learning pipeline with a single `config` object,
that can be customized from command line, passed to each step of the pipeline, and then dumped to a file for future reference.

This can be done by defining a custom model, and then by simply activating the `singleton` keyword argument of the `@command` decorator:

```python  title="singleton_config.py" linenums="1" hl_lines="19"
{!examples/composition/singleton.py!}
```

Argdantic will then use the defined argument as the root model, without wrapping it into a new one. This has the added
benefit of removing the top-level name from the CLI fields, which would be all the same in this case.
Note the absence of the `item` name in front of the following fields:

```console
$ python singleton.py --help
> usage: test.py [-h] --name TEXT --description TEXT --image.name TEXT
>
> optional arguments:
>   -h, --help          show this help message and exit
>   --name TEXT         (required)
>   --description TEXT  (required)
>   --image.name TEXT   (required)
```

!!! warning

    The `singleton` configuration setup only works when two requirements are met: first, **only one argument** must be
    defined in the signature of the `@command` function, and second, **that argument must be a _pydantic_ model**.
    Failure to meet these requirements will result in an `AssertionError` being raised.

## Nested Parsers

`argdantic` also allows to organize your code into a series of commands and subcommands, each with its own set of arguments.
A single parser is enough to define a list of commands at the same level.
However, sometimes it is necessary to define a hierarchy of commands, such as `git commit` and `git push`.

This can be done by defining multiple parsers, each with its own set of commands, and then merging them together, like so:

```python  title="nested_parsers.py" linenums="1" hl_lines="3 4 31-33"
{!examples/composition/nested_parsers.py!}
```

There are a few things to notice here:

 - The subparsers _must_ have a name, which is used to identify them when calling the CLI.
   This can be provided by either providing a `name` during instantiation, or by passing a `name` keyword argument to the `add_parser` method.

 - In general, the main parser _does not_ require a name, unless it is used as a subparser of another parser.

When executing the `help` command, the following output will be produced:

```console
$ python nested_parsers.py --help
> usage: nested_parsers.py [-h] <command> ...
>
> positional arguments:
>   <command>
>     users
>     books
>
> optional arguments:
>   -h, --help  show this help message and exit
```

!!! note

    The description provided by the `help` command is quite limited at the moment: as you can see, the name of the
    subparsers is shown, but not their description. This is a known limitation, and it will be addressed in the future.

The same can be done on the subgroup, calling the `help` command on the `users` subparser:

```console
$ python nested_parsers.py users --help
> usage: nested_parsers.py users [-h] <command> ...
>
> positional arguments:
>   <command>
>     add-user   Adds a single user.
>     delete-user
>                Deletes a user by name.
>
> optional arguments:
>   -h, --help   show this help message and exit
```

Finally, the `help` command can be called on the subcommand, showing the description and the arguments:

```console
$ python nested_parsers.py users add-user --help
> usage: nested_parsers.py users add-user [-h] --name TEXT --age INT
>
> optional arguments:
>   -h, --help   show this help message and exit
>   --name TEXT  (required)
>   --age INT    (required)
```

Last but not least, the command can be executed, by passing the required arguments:

```console
$ python nested_parsers.py users add-user --name "John Doe" --age 30
> Adding user: John Doe (30)
```

Of course, nested models and nested parsers can be combined together, to create a complex hierarchy of commands and arguments.
Fantasy is the limit, well, at least until you run out of RAM.
