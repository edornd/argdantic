# Commands

`@app.command` registers a function as a command. The command name is the function name in kebab case, so `add_note` is called as `add-note`.

## Parameters become flags

Each parameter becomes a flag named after it in kebab case: `max_items` becomes `--max-items`. A one-letter parameter gets a short flag: `n` becomes `-n`. pydantic validates every value against the parameter's type hint. Scalar types such as `int`, `Path`, `date`, `Literal` and enums work as flags.

- A parameter without a default is required.
- A parameter with a default is optional.
- A `bool` parameter gets a pair of flags, `--pinned` and `--no-pinned`.

pydantic's `Field` adds constraints and a description. Put it in an `Annotated` type hint or use it as the default, as in a pydantic model:

```python
@app.command
def add(
    title: Annotated[str, Field(min_length=1)],
    priority: int = Field(1, ge=0, description="higher comes first"),
) -> None:
    """Add a note."""
```

Flags must be spelled in full. argdantic does not expand a prefix such as `--ti` to `--title`.

Input comes from flags and the defaults in code. A `BaseSettings` parameter also reads environment variables, see [Environment variables](#environment-variables).

## Config models

A parameter typed with a pydantic model gives one flag per nested field. The flag is the dotted path from the parameter name.

```python
from pydantic import BaseModel, Field

from argdantic import App, Flat

app = App("trainctl")


class Optim(BaseModel):
    lr: float = Field(0.1, gt=0, description="learning rate")


class TrainConfig(BaseModel):
    optim: Optim = Optim()
    epochs: int = 3


@app.command
def train(cfg: TrainConfig) -> TrainConfig:
    """Launch a training run."""
    return cfg


if __name__ == "__main__":
    app()
```

```console
$ python trainctl.py train --cfg.optim.lr 0.5 --cfg.epochs 4
{"optim": {"lr": 0.5}, "epochs": 4}
```

The command gets a `TrainConfig` with an `Optim` inside. An error on a nested field names its dotted path, for example `cfg.optim.lr`. `--help` lists the fields of each model in their own group, with their descriptions.

### Flat models

`Flat[Model]` leaves the parameter name out of the flags:

```python
@app.command
def train(cfg: Flat[TrainConfig], slurm: bool = False) -> TrainConfig:
    """Launch a training run."""
    return cfg
```

```console
$ python trainctl.py train --optim.lr 0.5 --epochs 4 --slurm
{"optim": {"lr": 0.5}, "epochs": 4}
```

A type checker reads `Flat[TrainConfig]` as `TrainConfig`. The model validates as it does anywhere else. Its validators see the raw flag values, and its config applies only to it. Error paths leave out the parameter name, so `--optim.lr -1` reports `optim.lr`.

The top-level fields of a `Flat` model share their flag names with the other parameters. When two of them give the same flag, `@app.command` raises an error at import. `Flat` takes a pydantic model class only.

### Defaults

- A model parameter with no default is optional when every field of the model has a default. argdantic builds the model when the command runs.
- When a required field of the model gets no flag, the error names that field: `cfg.size`, or `size` for a `Flat` parameter.
- With a default instance, the flags change only the fields they name. `cfg: TrainConfig = TrainConfig(epochs=5)` with `--cfg.optim.lr 0.5` gives `lr=0.5` and keeps `epochs=5`. `--help` shows the values of the instance.
- A `Field(default_factory=...)` default works the same way. The flags change the fields they name in the factory's result.

### Environment variables

A parameter typed with a `BaseSettings` model from pydantic-settings reads environment variables as its own config says, for example with `env_prefix`, `env_file` or `secrets_dir`. A flag wins over an environment variable, and an environment variable wins over the default.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Cluster(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRAIN_")

    nodes: int = 1


@app.command
def launch(cluster: Cluster) -> Cluster:
    """Launch on the cluster."""
    return cluster
```

```console
$ TRAIN_NODES=4 python trainctl.py launch
{"nodes": 4}
$ TRAIN_NODES=4 python trainctl.py launch --cluster.nodes 8
{"nodes": 8}
```

- A default instance such as `cluster: Cluster = Cluster()` reads the environment once, when Python imports the module. Leave out the default to read it each time the command runs.
- `--help` shows the default in code, not the value from the environment.

Plain parameters and parameters typed with a plain `BaseModel` do not read environment variables.

## Help text

The first line of the docstring is the command's summary, shown in `--help` for the CLI and for the command. Parameter descriptions come from the `Args:` section of a Google-style docstring, or from `Field(description=...)`. When both are set, the `Field` wins.

## Groups

A group is an `App` mounted on another `App` with `add`. The group's name is the word that selects it on the command line.

```python
from argdantic import App

notes = App("notes", description="Work with notes.")


@notes.command
def add(title: str) -> str:
    """Add a note."""
    return title


cli = App("cli", description="Manage notes.")
cli.add(notes)

if __name__ == "__main__":
    cli()
```

```console
$ python cli.py notes add --title milk
"milk"
```

- Groups nest to any depth. Mount one group on another with `add`.
- A mounted `App` still runs alone, so `notes(["add", "--title", "milk"])` works, and a group can live in its own module.
- `add` mounts the `App` itself, not a copy. A command registered on `notes` after `cli.add(notes)` is still available through `cli`.
- `description` is the help text of an `App`. `python cli.py --help` shows the description of `cli`, then each command and group with its summary. The summary of a group is the first line of its description. `python cli.py notes --help` shows the full description of `notes`.
- The names at one level are unique. Two commands with the same name, a command and a group with the same name, or an `App` mounted below itself raise an error when the module is imported.

## Results

The return type hint decides how the result is serialised. With no return type hint, argdantic treats the result as `Any`. A pydantic model, a dataclass, a dict or a plain value prints as one JSON document on stdout. A command that returns `None` prints nothing. Exit code 0 means success.

## Safety hints

`@app.command` takes four optional hints that describe what a command does: `read_only`, `destructive`, `idempotent` and `open_world`. They follow the tool annotations of the Model Context Protocol.

```python
@app.command(destructive=True)
def remove(title: str) -> None:
    """Remove notes by title."""
```

argdantic stores the hints but does not act on them yet.
