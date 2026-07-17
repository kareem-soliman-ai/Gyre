"""Proprietary controller layer (stub).

This file is the ONLY thing in this package that ships publicly; everything
else under ``control/proprietary/`` is gitignored, mirroring
``gyre.providers.proprietary``. The reasoning is the same fence, one layer up:
the control seam, the reference controllers, and the controller-gap experiment
are open, but a controller that adaptively decides an agent's mode-switching is
Tier 3 — it needs to be built against validated sensors and validated itself
before it is handed a confident voice (see loops/L7-meta-loop.md).

If you have dropped proprietary controller modules alongside this file, each one
only needs to expose::

    def register_controllers(register):
        register("psy:my-controller", MyControllerFactory)

and ``register_all`` below will discover it. In a clean public checkout there
are no sibling modules, so this is a no-op and the package runs on the
reference controllers.
"""

from __future__ import annotations

from typing import Callable


def register_all(register: Callable[[str, Callable[[], object]], None]) -> None:
    """Discover and register any proprietary controller modules present."""
    import importlib
    import pkgutil

    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{mod.name}")
        except Exception:  # noqa: BLE001 - a broken private module must not break discovery
            continue
        hook = getattr(module, "register_controllers", None)
        if callable(hook):
            hook(register)
