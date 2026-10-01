from pathlib import Path

import pytest

from app.services.local_storage import LocalFileStorage, StorageError


def test_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.path_for("../outside.stl")


def test_storage_can_resume_from_database_offset(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    storage.create_empty("uploads/file.part")
    storage.append("uploads/file.part", offset=0, data=b"abcdef")

    resulting_size = storage.append("uploads/file.part", offset=3, data=b"XYZ")

    assert resulting_size == 6
    assert storage.path_for("uploads/file.part").read_bytes() == b"abcXYZ"


def test_storage_promotes_completed_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    storage.create_empty("uploads/file.part")
    storage.append("uploads/file.part", offset=0, data=b"stl-data")

    storage.promote("uploads/file.part", "cases/example/scan/v1.stl")

    assert not storage.path_for("uploads/file.part").exists()
    assert storage.path_for("cases/example/scan/v1.stl").read_bytes() == b"stl-data"
