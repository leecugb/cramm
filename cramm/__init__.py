# CRAMM — general-purpose hyperspectral mineral identification toolkit.
# USGS MICA decision-rule system, extended: secondary-feature depth-ratio
# constraint, wavelength-arbitrated muscovite subtyping, and quantitative
# muscovite composition mapping. Sensor-agnostic core with built-in EMIT L2A
# and ENVI Standard HDR adapters, plus the generic band-configuration contract
# for custom readers. Pure Python, zero GUI deps.

from .mica_engine import MicaEngine, ProcessResult

__version__ = "1.6.0"
__all__ = ["MicaEngine", "ProcessResult", "__version__"]
