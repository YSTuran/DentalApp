import mmap
import os
import struct
from pathlib import Path
from uuid import uuid4

MAX_PREVIEW_TRIANGLES = 250_000
MAX_ASCII_PREVIEW_BYTES = 32 * 1024 * 1024
TRIANGLE_BYTES = 50


class StlPreviewError(RuntimeError):
    pass


def _binary_triangle_count(path: Path) -> int | None:
    size = path.stat().st_size
    if size < 84:
        return None
    with path.open("rb") as handle:
        handle.seek(80)
        count = int.from_bytes(handle.read(4), "little")
    return count if size == 84 + count * TRIANGLE_BYTES else None


def preview_path(
    source: Path,
    *,
    cache_root: Path,
    content_hash: str,
    max_triangles: int = MAX_PREVIEW_TRIANGLES,
    max_ascii_bytes: int = MAX_ASCII_PREVIEW_BYTES,
) -> tuple[Path, bool]:
    """Return an immutable, browser-sized STL without loading the source into memory."""
    source_size = source.stat().st_size
    triangle_count = _binary_triangle_count(source)
    if triangle_count is None:
        if source_size > max_ascii_bytes:
            raise StlPreviewError("large_ascii_stl_preview_unavailable")
        return source, False
    if triangle_count <= max_triangles:
        return source, False

    stride = max(1, (triangle_count + max_triangles - 1) // max_triangles)
    displayed_count = (triangle_count + stride - 1) // stride
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / f"{content_hash}-{max_triangles}.stl"
    expected_size = 84 + displayed_count * TRIANGLE_BYTES
    if target.is_file() and target.stat().st_size == expected_size:
        return target, True

    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        with source.open("rb") as source_handle, temporary.open("xb") as output:
            output.write(b"DentalApp browser preview".ljust(80, b" "))
            output.write(struct.pack("<I", displayed_count))
            with mmap.mmap(source_handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
                batch = bytearray()
                for triangle in range(0, triangle_count, stride):
                    offset = 84 + triangle * TRIANGLE_BYTES
                    batch.extend(mapped[offset : offset + TRIANGLE_BYTES])
                    if len(batch) >= 1024 * 1024:
                        output.write(batch)
                        batch.clear()
                if batch:
                    output.write(batch)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise StlPreviewError("stl_preview_generation_failed") from error
    return target, True
