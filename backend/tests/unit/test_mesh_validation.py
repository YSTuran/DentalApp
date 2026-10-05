from pathlib import Path

import pytest
import trimesh

from app.models import MeshValidationStatus
from app.services.mesh_validation import MeshInspectionError, inspect_stl


def _export_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    path.write_bytes(mesh.export(file_type="stl"))


def test_missing_storage_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(MeshInspectionError, match="depolama dosyası bulunamadı"):
        inspect_stl(tmp_path / "missing.stl")


def test_closed_mesh_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "closed.stl"
    _export_stl(trimesh.creation.icosphere(subdivisions=1, radius=10), path)

    result = inspect_stl(path)

    assert result.status == MeshValidationStatus.VALID
    assert result.report["is_watertight"] is True
    assert result.report["boundary_edge_count"] == 0
    assert result.report["issues"] == []


def test_open_mesh_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "open.stl"
    mesh = trimesh.Trimesh(
        vertices=[[0, 0, 0], [10, 0, 0], [0, 10, 0]],
        faces=[[0, 1, 2]],
        process=False,
    )
    _export_stl(mesh, path)

    result = inspect_stl(path)

    assert result.status == MeshValidationStatus.INVALID
    assert result.report["is_watertight"] is False
    assert result.report["boundary_edge_count"] == 3
    assert "mesh_open_boundary" in result.report["issues"]


def test_intersecting_closed_components_are_invalid(tmp_path: Path) -> None:
    path = tmp_path / "intersecting.stl"
    first = trimesh.creation.box()
    second = trimesh.creation.box()
    second.apply_transform(trimesh.transformations.rotation_matrix(0.4, [0, 0, 1]))
    second.apply_translation([0.3, 0.2, 0.1])
    _export_stl(trimesh.util.concatenate([first, second]), path)

    result = inspect_stl(path)

    assert result.status == MeshValidationStatus.INVALID
    assert result.report["self_intersection_check"] == "pymeshlab"
    assert result.report["self_intersecting_face_count"] > 0
    assert "mesh_self_intersections" in result.report["issues"]
