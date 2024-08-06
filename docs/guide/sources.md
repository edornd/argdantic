# CLI Sources

`argdantic` allows you to define the arguments of your CLI in a variety of ways, including:

- Command line arguments, using `argparse`

- Environment variables or `.env` files, using [python-dotenv](https://github.com/theskumar/python-dotenv)

- Configuration files, using [JSON](https://www.json.org/json-en.html), [YAML](https://yaml.org/), or [TOML](https://toml.io/en/) files.

Each of these input sources can be used independently, or in combination with each other.
The priority of the input sources is given by the order in which they are defined, with the last one having the highest priority.
Of course, the command line arguments always have the highest priority, and they can be used to override any other input source.

Since every command is virtually independent, **sources are part of the command definition**.
This means that you can define different sources for different commands or models in the same CLI.

## Static Sources

The simplest kind of source is a static source, where the values are defined at the time of the command definition.

For instance, the following example defines a single command with many different sources:

```python  title="sources.py" linenums="1" hl_lines="6-11 31-36"
{!examples/sources/single_cmd.py!}
```

If you try to run the command as it is, you will get an error because the JSON and TOML files are not defined.
Comment out the lines that define the JSON and TOML sources, and run the command again.
You will see that the command runs successfully, and the arguments are taken from the YAML file:

```bash
$ python sources.py
> name='example' description='Example item' price=2.3 tags={'example', 'item', 'tag'} image=Image(url='https://example.com/image.jpg', name='example.jpg')
```

!!! warning

    Support for sources is still experimental, and the API may change in the future.
    The `required` flags are currently a limitation for file sources, as they force users
    to define CLI arguments that may be set via file.
    **Use default values or `None` as a workaround.**

## Dynamic Sources

Reading or writing a full configuration from scratch may not be your cup of tea.
Sometimes you may want to define a model with its own fields, reading its configuration
from a file, while still being able to override some of its fields from the command line.

Imagine you have a model like this:

```python title="models.py" linenums="1"
from pydantic import BaseModel

class Fruit(BaseModel):
    name: str
    color: str
    price: float
```

The CLI may define a `--fruit` argument to point to a file with the content of a `Fruit` instance, as well as a `--fruit.name` argument,  or `--fruit.color` argument, etc.

In argdantic, you can do that with the `from_file` annotation.

```python  title="dynamic.py" linenums="1" hl_lines="4 7 14"
{!examples/sources/dynamic.py!}
```

without additional configuration, the `from_file` decorator will automatically add an extra argument, equal to the name of the field, to the command line interface, in this case `--dataset` and `--optim`:

This will enable two extra arguments, namely `--dataset` and `--optim:

```diff
$ python dynamic.py --help
 usage: models.py [-h] [--dataset.name TEXT] [--dataset.batch-size INT] [--dataset.tile-size INT] [--dataset.shuffle | --no-dataset.shuffle] --dataset PATH
                  [--optim.name TEXT] [--optim.learning-rate FLOAT] [--optim.momentum FLOAT] --optim PATH

 options:
   -h, --help            show this help message and exit
   --dataset.name TEXT   (default: CIFAR10)
   --dataset.batch-size INT
                         (default: 32)
   --dataset.tile-size INT
                         (default: 256)
   --dataset.shuffle     (default: True)
   --no-dataset.shuffle
+   --dataset PATH        (required)
   --optim.name TEXT     (default: SGD)
   --optim.learning-rate FLOAT
                         (default: 0.01)
   --optim.momentum FLOAT
                         (default: 0.9)
+   --optim PATH          (required)
```

Invoking the command with the `--dataset` and `--optim` arguments will read the configuration from the files, which are defined as follows:

```yaml  title="resources/dataset.yml"
{!examples/sources/resources/dataset.yml!}
```

```yaml  title="resources/optim.yml"
{!examples/sources/resources/optim.yml!}
```

```console
$ python dynamic.py --dataset resources/dataset.yml --optim resources/optim.yml
 name='coco' batch_size=32 tile_size=512 shuffle=True
 name='adam' learning_rate=0.001 momentum=0.9
```

### Customizing the `from_file` behavior

The `from_file` decorator has a few options that can be used to customize its behavior:

- `required`: If `True`, the file path is required. If `False`, the file path is optional. Defaults to `True`.

- `loader`: A function that takes as input the model class itself, and the file path, and returns an instance of the model. `argdantic` provides three built-in loaders:
    - `JsonFileLoader`
    - `YamlFileLoader`
    - `TomlFileLoader`

- `use_field`: When specified, the model field indicated by the string will be used as the file path to look for the configuration.
In this case, the extra argument will not be added to the command line interface, and the file path is naturally provided by the pydantic model itself. It may be useful when the file path is needed later on.

Here's an example providing both the `required` and `use_field` options:

```python  title="dynamic_custom.py" linenums="1" hl_lines="6 9 17"
{!examples/sources/dynamic_custom.py!}
```

Specifying the following command will read the configuration from the optim instance only:

```diff
+$ python dynamic_custom.py --optim.path resources/optim.yml
name='CIFAR10' batch_size=32 tile_size=256 shuffle=True
path=PosixPath('resources/optim.yml') name='adam' learning_rate=0.001 momentum=0.9
```

Notice that the path this time is provided using a standard field, but the loader automatically reads the configuration from the specified file.
