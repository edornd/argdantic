# Input Sources

`argdantic` allows you to define the arguments of your CLI in a variety of ways, including:

- Command line arguments, using `argparse`

- Environment variables or `.env` files, using [python-dotenv](https://github.com/theskumar/python-dotenv)

- Configuration files, using [JSON](https://www.json.org/json-en.html), [YAML](https://yaml.org/), or [TOML](https://toml.io/en/) files.

Each of these input sources can be used independently, or in combination with each other.
The priority of the input sources is given by the order in which they are defined, with the last one having the highest priority.
Of course, the command line arguments always have the highest priority, and they can be used to override any other input source.

Since every command is virtually independent, **sources are part of the command definition**.
This means that you can define different sources for different commands in the same CLI.

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

## Sourced Models

Reading the full configuration may not be your cup of tea.
Sometimes you may want to define a model with its own fields, configurable from CLI, while also being able to read its configuration
from a file or environment variables.

Imagine you have a model like this:

```python title="models.py" linenums="1"
from pydantic import BaseModel

class Fruit(BaseModel):
    name: str
    color: str
    price: float
```

The CLI may define a `--fruit` argument to point to a file with the `Fruit` model, as well as a `--fruit.name` argument,  or `--fruit.color` argument, etc.

You can do that with ad-hoc models, named `YamlModel`, `JsonModel`, and `TomlModel`.

```python  title="models.py" linenums="1" hl_lines="2 5 11"
{!examples/sources/models.py!}
```

This will enable two extra arguments, namely `--dataset` and `--optim:

```console
$ python models.py --help
>usage: models.py [-h] [--dataset.name TEXT] [--dataset.batch-size INT] [--dataset.tile-size INT] [--dataset.shuffle | --no-dataset.shuffle] --dataset PATH
>                 [--optim.name TEXT] [--optim.learning-rate FLOAT] [--optim.momentum FLOAT] --optim PATH
>
>options:
>  -h, --help            show this help message and exit
>  --dataset.name TEXT   (default: CIFAR10)
>  --dataset.batch-size INT
>                        (default: 32)
>  --dataset.tile-size INT
>                        (default: 256)
>  --dataset.shuffle     (default: True)
>  --no-dataset.shuffle
>  --dataset PATH        (required)
>  --optim.name TEXT     (default: SGD)
>  --optim.learning-rate FLOAT
>                        (default: 0.01)
>  --optim.momentum FLOAT
>                        (default: 0.9)
>  --optim PATH          (required)
```

Invoking the command with the `--dataset` and `--optim` arguments will read the configuration from the files, which are defined as follows:

```yaml  title="resources/dataset.yml"
{!examples/sources/resources/dataset.yml!}
```

```yaml  title="resources/optim.yml"
{!examples/sources/resources/optim.yml!}
```

```console
$ python models.py --dataset resources/dataset.yml --optim resources/optim.yml
> name='coco' batch_size=32 tile_size=512 shuffle=True
> name='adam' learning_rate=0.001 momentum=0.9
```

!!! warning

    `YamlModel`, `JsonModel`, and `TomlModel` are still experimental, and the API may change in the future.
