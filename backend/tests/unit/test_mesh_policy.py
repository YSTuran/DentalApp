from app.models import CaseFileKind, MeshValidationStatus
from app.services.mesh_policy import apply_mesh_policy
from app.services.mesh_validation import MeshInspectionResult


def inspection_result(*issues: str) -> MeshInspectionResult:
    return MeshInspectionResult(
        status=MeshValidationStatus.INVALID if issues else MeshValidationStatus.VALID,
        report={"issues": list(issues)},
    )


def test_scan_topology_problems_become_review_warnings() -> None:
    result = apply_mesh_policy(
        inspection_result("mesh_open_boundary", "mesh_self_intersections"),
        file_kind=CaseFileKind.SCAN,
    )

    assert result.status == MeshValidationStatus.VALID
    assert result.report["validation_policy"] == "scan_reviewable"
    assert result.report["warnings"] == [
        "mesh_open_boundary",
        "mesh_self_intersections",
    ]
    assert result.report["blocking_issues"] == []


def test_scan_unknown_or_unsafe_problem_remains_invalid() -> None:
    result = apply_mesh_policy(
        inspection_result("mesh_non_finite_vertices"),
        file_kind=CaseFileKind.SCAN,
    )

    assert result.status == MeshValidationStatus.INVALID
    assert result.report["blocking_issues"] == ["mesh_non_finite_vertices"]


def test_design_keeps_all_mesh_problems_blocking() -> None:
    result = apply_mesh_policy(
        inspection_result("mesh_open_boundary"),
        file_kind=CaseFileKind.DESIGN,
    )

    assert result.status == MeshValidationStatus.INVALID
    assert result.report["validation_policy"] == "design_strict"
    assert result.report["warnings"] == []
    assert result.report["blocking_issues"] == ["mesh_open_boundary"]
