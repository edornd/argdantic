from importlib.metadata import version

from argdantic.app import App
from argdantic.errors import CommandError

__version__ = version("argdantic")
__all__ = ["App", "CommandError", "__version__"]
