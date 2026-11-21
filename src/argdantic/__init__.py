from importlib.metadata import version

from argdantic.app import App, Flat
from argdantic.errors import CommandError

__version__ = version("argdantic")
__all__ = ["App", "CommandError", "Flat", "__version__"]
