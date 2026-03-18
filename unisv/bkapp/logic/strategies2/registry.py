"""Registry for stock selection strategy classes under bkapp.logic.strategies2.

This module discovers and registers all StockSelectionStrategyBase subclasses found
in the `bkapp.logic.strategies2` package (including subpackages).
"""

import pkgutil
import importlib
import inspect
import logging
from typing import Optional

from .base import StockSelectionStrategyBase

strategy2_registry = {}


def load_strategies(package: Optional[object] = None, recursive: bool = True) -> None:
    """Discover and register StockSelectionStrategyBase subclasses from a package.

    - If `package` is None, uses the current package (where this file lives).
    - `recursive` controls whether to traverse subpackages.
    """
    if package is None:
        package = importlib.import_module(__package__)

    pkg_name = package.__name__
    if not hasattr(package, "__path__"):
        # Not a package
        return

    for finder, module_name, ispkg in pkgutil.iter_modules(package.__path__):
        full_name = f"{pkg_name}.{module_name}"
        try:
            module = importlib.import_module(full_name)
        except Exception:
            logging.exception("Failed to import stock strategy module %s", full_name)
            continue

        # find classes defined in the module that subclass StockSelectionStrategyBase
        for _, obj in inspect.getmembers(module, inspect.isclass):
            # ignore classes not defined in this module (avoid imports)
            if getattr(obj, "__module__", None) != module.__name__:
                continue
            if issubclass(obj, StockSelectionStrategyBase) and obj is not StockSelectionStrategyBase:
                key = getattr(obj, "name", obj.__name__)
                strategy2_registry[key] = obj

        # recurse into subpackages
        if recursive and ispkg:
            try:
                subpkg = importlib.import_module(full_name)
            except Exception:
                logging.exception("Failed to import subpackage %s", full_name)
                continue
            load_strategies(package=subpkg, recursive=recursive)


def get_strategy(name: str):
    """Return the strategy class registered under `name` or None."""
    return strategy2_registry.get(name)


def list_strategies():
    """Return a sorted list of registered strategy keys."""
    return sorted(strategy2_registry.keys())


# initialize when module is imported
load_strategies()


if __name__ == "__main__":
    # simple manual test
    print("Discovered stock selection strategies:")
    for k in list_strategies():
        cls = get_strategy(k)
        print(f"- {k}: {cls}")
