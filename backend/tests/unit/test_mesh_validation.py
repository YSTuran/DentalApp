from pathlib import Path

import trimesh

from app.models import MeshValidationStatus
from app.services.mesh_validation import inspect_stl


def _export_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    path.write_bytes(mesh.export(file_type="stl"))


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
