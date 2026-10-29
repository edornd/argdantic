from importlib.metadata import version

from argdantic._errors import CommandError
from argdantic.app import App

__version__ = version("argdantic")
__all__ = ["App", "CommandError", "__version__"]
