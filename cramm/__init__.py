# CRAMM — EMIT hyperspectral mineral identification toolkit.
# USGS MICA decision-rule system, extended: secondary-feature depth-ratio
# constraint, wavelength-arbitrated muscovite subtyping, and quantitative
# muscovite composition mapping. Pure Python, zero GUI dependencies.

from .mica_engine import MicaEngine, ProcessResult

__all__ = ["MicaEngine", "ProcessResult"]
