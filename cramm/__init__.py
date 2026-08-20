# MICA Desktop App — Core Engine
# This module encapsulates the entire core logic of the MICA mineral
# identification algorithm, with zero Qt dependencies.

from .mica_engine import MicaEngine, ProcessResult

__all__ = ["MicaEngine", "ProcessResult"]
