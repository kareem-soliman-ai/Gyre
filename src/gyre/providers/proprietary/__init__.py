"""Proprietary provider layer (stub).

This file is the ONLY thing in this package that ships publicly. Everything else
under ``proprietary/`` is gitignored. That is deliberate: the measurement seam,
the naive baselines, and the benchmark are open, but validated latent-variable
measurements are the part that takes real psychometric work to build and validate,
and they live behind this fence.

If you have dropped proprietary provider modules alongside this file, define a
``register_all(register)`` function (here or in a submodule you import here) that
registers them with the registry. The public ``gyre.providers`` package calls it
best-effort on import. If you have not, this stub does nothing and the package
runs on the naive baselines.

To build your own measurements (proprietary or not), see
docs/building-measurements.md. To place them here so they load automatically,
implement ``MeasurementProvider`` and register them below.
"""

from __future__ import annotations

from typing import Callable

from gyre.measurement import MeasurementProvider


def register_all(register: Callable[[str, Callable[[], MeasurementProvider]], None]) -> None:
    """Discover and register any proprietary provider modules present.

    This walks the sibling modules in this (gitignored) package and calls each
    one's ``register_providers(register)`` if it defines one. In a clean public
    checkout there are no sibling modules, so this is a no-op and everything runs
    on the naive baselines. In a checkout that has the private layer, each gitignored
    provider module registers itself here without any tracked code naming it.

    A provider module only needs to expose::

        def register_providers(register):
            register("psy:my-provider", MyProviderFactory)
    """
    import importlib
    import pkgutil

    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{mod.name}")
        except Exception:  # noqa: BLE001 - a broken private module must not break discovery
            continue
        hook = getattr(module, "register_providers", None)
        if callable(hook):
            hook(register)
