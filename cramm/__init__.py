# CRAMM — EMIT hyperspectral mineral identification toolkit.
# USGS MICA decision-rule system, extended: secondary-feature depth-ratio
# constraint, wavelength-arbitrated muscovite subtyping, and quantitative
# muscovite composition mapping. Pure Python, zero GUI dependencies.

# Lazy export (PEP 562): `python -m cramm.mica_engine` would otherwise hit a
# runpy RuntimeWarning, because an eager `from .mica_engine import ...` here
# puts cramm.mica_engine into sys.modules before runpy executes it as __main__.
from typing import TYPE_CHECKING

__all__ = ["MicaEngine", "ProcessResult"]


def __getattr__(name: str):
    if name in __all__:
        from . import mica_engine
        return getattr(mica_engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:  # static analysis / IDE completion still sees the real types
    from .mica_engine import MicaEngine, ProcessResult
