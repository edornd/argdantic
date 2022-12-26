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

!!! warning

    Documentation under construction, be patient!
