# CRAMM — general-purpose hyperspectral mineral identification toolkit.
# USGS MICA decision-rule system, extended: secondary-feature depth-ratio
# constraint, wavelength-arbitrated muscovite subtyping, and quantitative
# muscovite composition mapping. Sensor-agnostic core (EMIT L2A is the
# built-in reader, one supported input type). Pure Python, zero GUI deps.

from .mica_engine import MicaEngine, ProcessResult

__all__ = ["MicaEngine", "ProcessResult"]
