import numpy as np
import pytest

from cramm.envi_reader import EnviReader
from cramm.envi_writer import EnviResultWriter
from cramm.mica_engine import MicaEngine


def _write_case(tmp_path, *, interleave="bil", data_type=4, byte_order=0,
                units="Nanometers", include_fwhm=True, offset=0,
                scale=None, good=None, ignore=None, dtype_override=None):
    cube = (np.arange(24, dtype=np.float64).reshape(2, 3, 4) + 1) / 25.0
    disk = {
        "bsq": cube.transpose(2, 0, 1),
        "bil": cube.transpose(0, 2, 1),
        "bip": cube,
    }[interleave]
    dtype_code = {
        1: "u1", 2: "i2", 3: "i4", 4: "f4", 5: "f8",
        12: "u2", 13: "u4", 14: "i8", 15: "u8",
    }[data_type]
    dtype = np.dtype(("<" if byte_order == 0 else ">") + dtype_code)
    if dtype_override is not None:
        dtype = np.dtype(dtype_override)
    if scale is not None:
        disk = disk * scale
    if np.issubdtype(dtype, np.integer):
        disk = np.rint(disk)
    disk = disk.astype(dtype)
    binary = tmp_path / "cube.dat"
    with binary.open("wb") as stream:
        if offset:
            stream.write(b"\x00" * offset)
        stream.write(disk.tobytes(order="C"))
    is_nm = units.lower().startswith("nano") or units == "OMIT"
    wavelengths = "400, 500, 600, 700" if is_nm else "0.4, 0.5, 0.6, 0.7"
    widths = "10, 10, 10, 10" if is_nm else "0.01, 0.01, 0.01, 0.01"
    lines = [
        "ENVI", "samples = 3", "lines = 2", "bands = 4",
        f"header offset = {offset}", f"data type = {data_type}",
        f"interleave = {interleave}", f"byte order = {byte_order}",
        f"wavelength = {{{wavelengths}}}",
    ]
    if units != "OMIT":
        lines.append(f"wavelength units = {units}")
    if include_fwhm:
        lines.append(f"fwhm = {{{widths}}}")
    if scale is not None:
        lines.append(f"reflectance scale factor = {scale}")
    if ignore is not None:
        lines.append(f"data ignore value = {ignore}")
    if good is not None:
        lines.append("good_wavelengths = {" + ", ".join(map(str, good)) + "}")
    header = tmp_path / "cube.hdr"
    header.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return header, binary, cube


@pytest.mark.parametrize("interleave", ["bsq", "bil", "bip"])
def test_envi_interleaves_and_nm_units(tmp_path, interleave):
    header, _, cube = _write_case(tmp_path, interleave=interleave)
    spectrum, lon, lat, w, bp, wl, channels = EnviReader.load(str(header))
    assert spectrum.dtype == np.float32
    assert np.allclose(spectrum, cube, rtol=0, atol=1e-7)
    assert lon is None and lat is None
    assert np.allclose(w, [0.4, 0.5, 0.6, 0.7])
    assert np.allclose(bp, 0.01)
    assert np.array_equal(wl, w)
    assert np.array_equal(channels, np.arange(4))


def test_envi_int16_scale_ignore_big_endian_and_offset(tmp_path):
    header, binary, cube = _write_case(
        tmp_path, data_type=2, byte_order=1, offset=16, scale=10000, ignore=-9999
    )
    raw = binary.read_bytes()
    # Replace the first stored int16 with the ignore marker, preserving offset.
    raw = raw[:16] + np.array(-9999, dtype=">i2").tobytes() + raw[18:]
    binary.write_bytes(raw)
    spectrum, _, _, w, bp, _, _ = EnviReader.load(str(header))
    expected = np.rint(cube * 10000.0) / 10000.0
    expected[0, 0, 0] = 0
    assert np.allclose(spectrum, expected, rtol=0, atol=1e-7)
    assert np.allclose(w, [0.4, 0.5, 0.6, 0.7])
    assert np.allclose(bp, 0.01)


def test_envi_good_wavelengths_and_explicit_valid_bands(tmp_path):
    header, _, _ = _write_case(tmp_path, good=[1, 0, 1, 1])
    _, _, _, w, _, wl, channels = EnviReader.load(str(header))
    assert np.array_equal(channels, [0, 2, 3])
    assert np.allclose(wl, w[[0, 2, 3]])
    _, _, _, _, _, wl2, channels2 = EnviReader.load(str(header), valid_bands=[3, 1])
    assert np.array_equal(channels2, [3, 1])
    assert np.allclose(wl2, w[[3, 1]])


def test_envi_missing_units_infers_nm_for_wavelength_and_fwhm(tmp_path):
    header, _, _ = _write_case(tmp_path, units="OMIT")
    _, _, _, w, bp, _, _ = EnviReader.load(str(header))
    assert np.allclose(w, [0.4, 0.5, 0.6, 0.7])
    assert np.allclose(bp, 0.01)


def test_envi_fwhm_fallback_is_micrometres(tmp_path):
    header, _, _ = _write_case(tmp_path, include_fwhm=False, units="Micrometers")
    with pytest.raises(ValueError, match="FWHM"):
        EnviReader.load(str(header))
    _, _, _, _, bp, _, _ = EnviReader.load(str(header), fwhm=0.012)
    assert np.allclose(bp, 0.012)


def test_envi_binary_size_mismatch(tmp_path):
    header, binary, _ = _write_case(tmp_path)
    binary.write_bytes(binary.read_bytes()[:-1])
    with pytest.raises(ValueError, match="binary size mismatch"):
        EnviReader.load(str(header))


def test_envi_engine_facade(tmp_path):
    header, _, cube = _write_case(tmp_path, interleave="bip")
    spectrum, lon, lat, _, _, _, _ = MicaEngine.load_envi(str(header))
    assert np.allclose(spectrum, cube, rtol=0, atol=1e-7)
    assert lon is None and lat is None


def test_envi_writer_preserves_grid_and_inherits_crs(tmp_path):
    header, _, _ = _write_case(tmp_path)
    with header.open("a", encoding="utf-8") as stream:
        stream.write("map info = {UTM, 1.0, 1.0, 500000.0, 4600000.0, 30.0, 30.0, 47, North, WGS-84, units=Meters}\n")
        stream.write("coordinate system string = {PROJCS[\"WGS_1984_UTM_Zone_47N\"]}\n")
        stream.write("x start = 10\ny start = 20\n")
    rgb = np.arange(18, dtype=np.uint8).reshape(2, 3, 3)
    centers = np.linspace(2.1, 2.3, 6, dtype=np.float64).reshape(2, 3)
    prefix = tmp_path / "products" / "scene"
    written = EnviResultWriter.write(
        str(prefix), str(header), rgb, rgb, rgb, rgb, rgb,
        mus_center=centers, chl_center=centers, cal_center=centers, fd=centers,
    )
    assert len(written) == 12
    mapping_header = EnviReader.read_header(str(prefix.parent / "scene_mapping.hdr"))
    assert mapping_header["samples"] == "3"
    assert mapping_header["lines"] == "2"
    assert mapping_header["bands"] == "3"
    assert mapping_header["map info"].startswith("UTM, 1.0, 1.0, 500000.0")
    assert mapping_header["coordinate system string"] == 'PROJCS["WGS_1984_UTM_Zone_47N"]'
    assert mapping_header["x start"] == "10" and mapping_header["y start"] == "20"
    float_header = EnviReader.read_header(str(prefix.parent / "scene_float.hdr"))
    assert float_header["bands"] == "4"
    assert float_header["data type"] == "4"
    values = np.fromfile(prefix.parent / "scene_float.dat", dtype="<f4").reshape(2, 3, 4)
    assert np.allclose(values, np.stack([centers] * 4, axis=2), rtol=0, atol=1e-6)


def test_envi_writer_rejects_grid_mismatch(tmp_path):
    header, _, _ = _write_case(tmp_path)
    rgb = np.zeros((2, 3, 3), dtype=np.uint8)
    bad = np.zeros((1, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="does not match source"):
        EnviResultWriter.write(str(tmp_path / "bad"), str(header), bad, rgb, rgb, rgb, rgb)
