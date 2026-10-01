from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from app.models import MeshValidationStatus


class MeshInspectionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MeshInspectionResult:
    status: MeshValidationStatus
    report: dict[str, Any]


def _finite_float(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def inspect_stl(path: Path) -> MeshInspectionResult:
    try:
        loaded = trimesh.load_mesh(path, file_type="stl", process=True)
    except Exception as error:
        raise MeshInspectionError("STL dosyası ayrıştırılamadı.") from error

    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise MeshInspectionError("STL dosyasında üçgen mesh bulunamadı.")

    vertices = np.asarray(loaded.vertices, dtype=np.float64)
    faces = np.asarray(loaded.faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3:
        raise MeshInspectionError("STL mesh geometrisi üçgenlerden oluşmuyor.")
    if len(vertices) == 0 or len(faces) == 0:
        raise MeshInspectionError("STL mesh geometrisi boş.")
    if int(faces.min()) < 0 or int(faces.max()) >= len(vertices):
        raise MeshInspectionError("STL yüzeyleri geçersiz köşe indeksleri içeriyor.")

    finite_vertices = bool(np.isfinite(vertices).all())
    triangles = vertices[faces]
    cross_products = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    extents = np.asarray(loaded.extents, dtype=np.float64)
    diagonal = float(np.linalg.norm(extents)) if np.isfinite(extents).all() else 0.0
    degenerate_threshold = max(diagonal * diagonal * 1e-12, 1e-18)
    double_areas = np.linalg.norm(cross_products, axis=1)
    degenerate_face_count = int(np.count_nonzero(double_areas <= degenerate_threshold))

    canonical_faces = np.sort(faces, axis=1)
    _, duplicate_counts = np.unique(canonical_faces, axis=0, return_counts=True)
    duplicate_face_count = int(np.sum(np.maximum(duplicate_counts - 1, 0)))

    canonical_edges = np.sort(np.asarray(loaded.edges, dtype=np.int64), axis=1)
    _, edge_counts = np.unique(canonical_edges, axis=0, return_counts=True)
    boundary_edge_count = int(np.count_nonzero(edge_counts == 1))
    non_manifold_edge_count = int(np.count_nonzero(edge_counts > 2))

    with np.errstate(divide="ignore", invalid="ignore"):
        is_watertight = bool(loaded.is_watertight)
        is_winding_consistent = bool(loaded.is_winding_consistent)
        is_volume = bool(loaded.is_volume)
        surface_area = _finite_float(loaded.area)
        volume = _finite_float(abs(loaded.volume))

    issues: list[str] = []
    if not finite_vertices:
        issues.append("mesh_non_finite_vertices")
    if degenerate_face_count:
        issues.append("mesh_degenerate_faces")
    if duplicate_face_count:
        issues.append("mesh_duplicate_faces")
    if boundary_edge_count or not is_watertight:
        issues.append("mesh_open_boundary")
    if non_manifold_edge_count:
        issues.append("mesh_non_manifold_edges")
    if not is_winding_consistent:
        issues.append("mesh_inconsistent_winding")
    if not is_volume:
        issues.append("mesh_not_closed_volume")

    report: dict[str, Any] = {
        "validator": "trimesh",
        "vertex_count": int(len(vertices)),
        "face_count": int(len(faces)),
        "surface_area": surface_area,
        "volume": volume,
        "bounds": {
            "min": [_finite_float(value) for value in loaded.bounds[0]],
            "max": [_finite_float(value) for value in loaded.bounds[1]],
            "extents": [_finite_float(value) for value in extents],
        },
        "is_watertight": is_watertight,
        "is_winding_consistent": is_winding_consistent,
        "is_volume": is_volume,
        "boundary_edge_count": boundary_edge_count,
        "non_manifold_edge_count": non_manifold_edge_count,
        "degenerate_face_count": degenerate_face_count,
        "duplicate_face_count": duplicate_face_count,
        "self_intersection_check": "topology_only",
        "issues": issues,
    }
    status = MeshValidationStatus.VALID if not issues else MeshValidationStatus.INVALID
    return MeshInspectionResult(status=status, report=report)
