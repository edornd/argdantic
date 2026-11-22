from importlib.metadata import version

from argdantic.app import App, Arg, Flat
from argdantic.errors import CommandError

__version__ = version("argdantic")
__all__ = ["App", "Arg", "CommandError", "Flat", "__version__"]
