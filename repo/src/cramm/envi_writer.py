#!/usr/bin/env python
"""Write CRAMM products on the source ENVI grid without reprojection."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from .envi_reader import EnviReader

# Geolocation/projection fields copied verbatim from the source ENVI header.
_GEO_FIELDS = (
    "map info",
    "coordinate system string",
    "projection info",
    "rpc info",
    "geo points",
    "x start",
    "y start",
)


class EnviResultWriter:
    """Write same-grid ENVI Standard products and inherit source map metadata."""

    @staticmethod
    def _write_one(
        prefix: Path,
        array: np.ndarray,
        *,
        source_shape: Tuple[int, int],
        geo: Dict[str, str],
        description: str,
        band_names: Iterable[str],
        data_type: int,
        ignore_zero: bool = False,
    ) -> Tuple[Path, Path]:
        rows, cols = source_shape
        if array.ndim == 2:
            array = array[:, :, None]
        if array.shape[:2] != (rows, cols):
            raise ValueError(f"ENVI output grid {array.shape[:2]} does not match source {(rows, cols)}")
        if array.shape[2] < 1:
            raise ValueError("ENVI output must have at least one band")
        binary = prefix.with_suffix(".dat")
        header = prefix.with_suffix(".hdr")
        if binary.exists() or header.exists():
            raise FileExistsError(f"Refusing to overwrite existing ENVI product: {binary} / {header}")
        names = list(band_names)
        if len(names) != array.shape[2]:
            raise ValueError("ENVI band-name count does not match output bands")
        if data_type == 1:
            data = np.asarray(array, dtype=np.uint8)
        elif data_type == 4:
            data = np.asarray(array, dtype="<f4")
        else:
            raise ValueError(f"Unsupported output ENVI data type {data_type}")
        # BIP preserves [row, column, band] directly and never changes the grid.
        data.tofile(binary)
        lines = [
            "ENVI",
            f"description = {{{description}}}",
            f"samples = {cols}",
            f"lines = {rows}",
            f"bands = {data.shape[2]}",
            "header offset = 0",
            "file type = ENVI Standard",
            f"data type = {data_type}",
            "interleave = bip",
            "byte order = 0",
            "band names = {" + ", ".join(names) + "}",
        ]
        if ignore_zero:
            lines.append("data ignore value = 0")
        for key in _GEO_FIELDS:
            if key in geo:
                value = geo[key]
                if key in {"x start", "y start"}:
                    lines.append(f"{key} = {value}")
                else:
                    lines.append(f"{key} = {{{value}}}")
        header.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return binary, header

    @staticmethod
    def write(
        prefix: str,
        source_hdr: str,
        orth_rgb: np.ndarray,
        color_enhanced: np.ndarray,
        mus_image: np.ndarray,
        chl_image: np.ndarray,
        cal_image: np.ndarray,
        *,
        mus_center: Optional[np.ndarray] = None,
        chl_center: Optional[np.ndarray] = None,
        cal_center: Optional[np.ndarray] = None,
        fd: Optional[np.ndarray] = None,
    ) -> List[Path]:
        """Write five RGB products and, when supplied, four float products.

        Every output has exactly the source ``lines`` and ``samples``. Map and
        projection fields are copied verbatim; no orthorectification or
        coordinate transformation is performed.
        """
        source = Path(source_hdr)
        metadata = EnviReader.read_header(str(source))
        rows = int(metadata["lines"])
        cols = int(metadata["samples"])
        geo = {key: metadata[key] for key in _GEO_FIELDS if key in metadata}
        root = Path(prefix)
        root.parent.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []
        products = [
            ("mapping", orth_rgb, "CRAMM winner-rule mineral map"),
            ("color_enhanced", color_enhanced, "CRAMM color-enhanced mineral map"),
            ("mus", mus_image, "CRAMM muscovite absorption-center thematic map"),
            ("chl", chl_image, "CRAMM chlorite absorption-center thematic map"),
            ("cal", cal_image, "CRAMM carbonate absorption-center thematic map"),
        ]
        for suffix, array, description in products:
            written.extend(EnviResultWriter._write_one(
                Path(str(root) + "_" + suffix), array,
                source_shape=(rows, cols), geo=geo, description=description,
                band_names=("Red", "Green", "Blue"), data_type=1,
            ))
        centers = (mus_center, chl_center, cal_center, fd)
        if any(item is not None for item in centers):
            if not all(item is not None for item in centers):
                raise ValueError("All four float arrays are required when writing the center/fd product")
            stack = np.stack(centers, axis=2)
            written.extend(EnviResultWriter._write_one(
                Path(str(root) + "_float"), stack,
                source_shape=(rows, cols), geo=geo,
                description="CRAMM float absorption centers and fit-depth output",
                band_names=("mus_center_um", "chl_center_um", "cal_center_um", "fd"),
                data_type=4, ignore_zero=True,
            ))
        return written
