from importlib.metadata import version

from argdantic.app import App

__version__ = version("argdantic")
__all__ = ["App", "__version__"]
