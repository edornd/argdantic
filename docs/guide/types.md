# Field Types

Thanks to features provided by _pydantic_'s data definitions, `argdantic` supports a large amount of field types,
starting from the standard library up to JSON inputs.

## Primitive types

Considering primitive, non-complex data types, the library supports the following:

- `str`: values accepted as is, parsed as simple text without further processing.

- `int`: tries to convert any given input into an integer through `int(value)`.

- `float`: similarly, tries to convert any given input into a floating point number through `float(value)`.

- `bytes`: similar to strings, however in this case the underlying representation remains in bytes.

- `bool`: by default, booleans are intended as flag options. In this case any boolean field will have two corresponding CLI flags `--field/--no-field`.

The following example shows a brief overview of the primitive types:

```python title="primitives.py" linenums="1"
{!examples/typing/primitive.py!}
```

With the following help message:
```console
$ python primitives.py --help
> usage: primitives.py [-h] --name TEXT --age INT --weight FLOAT --data BYTES (--flag | --no-flag)
>
> optional arguments:
>   -h, --help      show this help message and exit
>   --name TEXT     (required)
>   --age INT       (required)
>   --weight FLOAT  (required)
>   --data BYTES    (required)
>   --flag
>   --no-flag
```

!!! note

    Observe that the `--flag` and `--no-flag` options are not marked as required.
    That is the expected behaviour: strictly speaking, _taken individually_, they are not required.
    However, being mutually exclusive, one of either `--flag` or `--no-flag` is still needed.

`argdantic`` takes care of converting the provided fields into _argparse_ arguments, so that the automatically generated description reamins as faithful as possible.
Bear in mind that types are exploited only for documentation purposes, the final type checking will be carried out by _pydantic_.
Most complex types are often interpreted as strings, unless specified otherwise.

## Complex types

Thanks to the powerful data definitions provided by _pydantic_, `argdantic` supports a large amount of complex types,
Currently, the following types have been tested and supported:

### Standard Library types

Generally speaking, non-typed complex types will default to strings unless specified otherwise.

- `list`: without specifying the internal type, _list_ fields will behave as _multiple_ options of string items.
Internally, _argdantic_ exploits _argparse's `nargs` option to handle sequences.
In this case, the argument can be repeated multiple times to build a list.
For instance, `python cli.py --add 1 2` will result in a list `[1, 2]`.

- `tuple`: similar to lists, this will behave as an unbounded sequence of strings, with multiple parameters.

- `dict`: dictionaries are interpreted as JSON strings. In this case, there will be no further validation.
Given that valid JSON strings require double quotes, arguments provided through the command line must use single-quoted strings.
For instance, `python cli.py --extras '{"items": 12}'` will be successfully parsed, while `python cli.py --extras "{'items': 12}"` will not.

- `set`: again, from a command line point of view, sets are a simple list of values. In this case, repeated values will be excluded.
For instance, `python cli.py --add a --add b --add a` will result in a set `{'a', 'b'}`.

- `frozenset`: _frozen_ sets adopt the same behavior as normal sets, with the only difference that they remain immutable.

- `deque`: similarly, _deques_ act as sequences from a CLI standpoint, while being treaded as double-ended queues in code.

- `range`: ranges are interpreted as a sequence of integers, with the same behavior as lists and tuples.

### Typing Containers

- `Any`: For obvious reasons, _Any_ fields will behave as `str` options without further processing.

- `Optional`: optional typing can be interpreted as _syntactic sugar_, meaning it will not have any effect on the underlying
validation, but it provides an explicit declaration that the field can also accept `None` as value.

- `List`: Similar to standard lists, typing _Lists_ behave as sequences of items. In this case however the inner type is
exploited to provide further validation through _pydantic_.
For instance, `python cli.py --add a --add b` will result in a validation error for a list of integers `List[int]`.

- `Tuple`: typing _Tuples_ can behave in two ways: when using a _variable length_ structure (i.e., `Tuple[int]` or `Tuple[int, ...]`),
tuples act as a sequence of typed items, validated through _pydantic, where the parameter is specified multiple times.
When using a _fixed length_ structure (i.e., `Tuple[int, int]` or similar), they are considered as fixed `nargs` options,
where the parameter is specified once, followed by the sequence of values separated by whitespaces.
 For instance . `python cli.py --items a b c` will results in a tuple `('a', 'b', 'c')`.
 If the `items` tuple specified only two items, the command will result in a validation error.

- `Dict`: Similar to the standard `dict` field, typing dictionaries require a JSON string as input. However, inner types
allow for a finer validation: for instance, considering a `metrics: Dict[str, float]` field, `--metrics '{"f1": 0.93}'` is accepted,
while `--metrics '{"auc": "a"}'` is not a valid input.

- `Deque`: with the same reasoning of typed lists and tuples, _Deques_ will act as sequences with a specific type.

- `Set`: As you guessed, typed sets act as multiple options where repeated items are excluded, with additional type validation
on the items themselves.

- `FrozenSet`: as with _Sets_, but they represent immutable structures after parsing.

- `Sequence` and `Iterables`: with no surpise, sequences and iterables act as sequences, nothing much to add here.

!!! warning

    for obvious reasons, `Union` typings are not supported at this time.
    Parsing a multi-valued parameter is really more of a phylosophical problem than a technical one.
    Future releases will consider the support for this typing.


The code below provides a relatively comprehensive view of most container types supported through `argdantic`.


```python  title="containers.py" linenums="1"
{!examples/typing/containers.py!}
```

Executing this script with the _help_ command will provide the description for the current configuration.
Also, defaults are allowed and validated.

```console
$ python containers.py --help
> usage: containers.py [-h] --simple-list TEXT [TEXT ...] --list-of-ints INT [INT ...]
>   --simple-tuple TEXT [TEXT ...] --multi-typed-tuple INT FLOAT TEXT BOOL --simple-dict JSON
>   --dict-str-float JSON --simple-set TEXT [TEXT ...] --set-bytes BYTES [BYTES ...]
>   --frozen-set INT [INT ...] --none-or-str TEXT --sequence-of-ints INT [INT ...]
>   --compound JSON --deque INT [INT ...]
>
> optional arguments:
>   -h, --help            show this help message and exit
>   --simple-list TEXT [TEXT ...]           (required)
>   --list-of-ints INT [INT ...]            (required)
>   --simple-tuple TEXT [TEXT ...]          (required)
>   --multi-typed-tuple INT FLOAT TEXT BOOL (required)
>   --simple-dict JSON                      (required)
>   --dict-str-float JSON                   (required)
>   --simple-set TEXT [TEXT ...]            (required)
>   --set-bytes BYTES [BYTES ...]           (required)
>   --frozen-set INT [INT ...]              (required)
>   --none-or-str TEXT                      (required)
>   --sequence-of-ints INT [INT ...]        (required)
>   --compound JSON                         (required)
>   --deque INT [INT ...]                   (required)
```


### Literals and Enums

Sometimes it may be useful to directly limit the choices of certain fields,
by letting the user select among a fixed list of values.
In this case, `argdantic` provides this feature using  _pydantic_'s support for `Enum` and `Literal` types,
parsed from the command line through the `choice` argument option.

While _Enums_ represent the standard way to provide choice-based options, _Literals_ can be seen as a lightweight enumeration.
In general, the latter are simpler and easier to handle than the former for most use cases.
_Enums_ on the other hand provide both a `name` and a `value` component, where only the former is exploited for the parameter definition.
The latter can represent any kind of object, therefore making _enums_ more suitable for more complex use cases.

The following script presents a sample of possible choice definitions in _clidantic_:
```python  title="choices.py" linenums="1"
{!examples/typing/choices.py!}
```

!!! warning

    As you probably noticed, the string enumeration only subclasses `Enum`.
    Strictly speaking, `ToolEnum(str, Enum)` would be a better inheritance definition, however this breaks the type
    inference by providing two origins.

    Currently, there are two solutions:

    - **simply use Enum**, it should be fine in most cases.
    - **use StrEnum**, which however is only available since Python 3.11.

Launching the help for this script will result in the following output:
```console
$ python choices.py --help
> usage: choices.py [-h] [--a [one|two]] [--b [1|2]] [--c [True|False]] [--d [hammer|screwdriver]] [--e [ok|not_found|internal_error]]
>
> optional arguments:
>   -h, --help            show this help message and exit
>   --a [one|two]                       (default: two)
>   --b [1|2]                           (default: 2)
>   --c [True|False]                    (default: True)
>   --d [hammer|screwdriver]            (default: ToolEnum.hammer)
>   --e [ok|not_found|internal_error]   (default: HTTPEnum.not_found)
```

You can notice that, even without explicit description,
choice-based fields will automatically provide the list of possible values.
Defaults also behave as expected: both literals and enums will accept any of the allowed values as default, and it that
case the selected item will be displayed as _default_ in the console.
Again, note that the CLI exploits the `name` field in enum-based arguments for readability, not its actual value.

Calling the script with a wrong choice will result in an error message, displaying the list of allowed values:
```console
$ python choices.py --a three
> usage: choices.py [-h] [--a [one|two]] [--b [1|2]] [--c [True|False]] [--d [hammer|screwdriver]] [--e [ok|not_found|internal_error]]
> choices.py: error: argument --a: invalid choice: three (choose from [one|two])
```

### Module types

!!! note

    Coming soon!
