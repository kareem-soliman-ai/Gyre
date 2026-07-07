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
    """Register proprietary providers with the registry.

    The public stub registers nothing. A private checkout replaces or extends this
    with real registrations, e.g.::

        from gyre.providers.proprietary.rumination_mvt import MvtRuminationProvider
        register("psy:mvt-rumination", MvtRuminationProvider)
    """
    return None
