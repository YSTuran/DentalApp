import struct

import pytest

from app.services.stl_preview import StlPreviewError, preview_path


def binary_stl(triangle_count: int) -> bytes:
    triangle = struct.pack("<12fH", *([0.0] * 12), 0)
    return b"test".ljust(80, b" ") + struct.pack("<I", triangle_count) + triangle * triangle_count


def test_binary_preview_is_decimated_without_changing_source(tmp_path) -> None:
    source = tmp_path / "source.stl"
    source.write_bytes(binary_stl(10))

    result, decimated = preview_path(
        source,
        cache_root=tmp_path / "previews",
        content_hash="a" * 64,
        max_triangles=3,
    )

    assert decimated is True
    assert result != source
    assert int.from_bytes(result.read_bytes()[80:84], "little") == 3
    assert int.from_bytes(source.read_bytes()[80:84], "little") == 10


def test_large_ascii_preview_is_rejected_before_browser_download(tmp_path) -> None:
    source = tmp_path / "ascii.stl"
    source.write_bytes(b"solid demo\nendsolid demo\n")

    with pytest.raises(StlPreviewError, match="large_ascii_stl_preview_unavailable"):
        preview_path(
            source,
            cache_root=tmp_path / "previews",
            content_hash="b" * 64,
            max_ascii_bytes=8,
        )
