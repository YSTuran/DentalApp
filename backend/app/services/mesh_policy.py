from app.models import CaseFileKind, MeshValidationStatus
from app.services.mesh_validation import MeshInspectionResult

SCAN_REVIEW_WARNINGS = frozenset(
    {
        "mesh_degenerate_faces",
        "mesh_duplicate_faces",
        "mesh_open_boundary",
        "mesh_non_manifold_edges",
        "mesh_inconsistent_winding",
        "mesh_not_closed_volume",
        "mesh_self_intersections",
    }
)


def apply_mesh_policy(
    result: MeshInspectionResult,
    *,
    file_kind: CaseFileKind,
) -> MeshInspectionResult:
    report = dict(result.report)
    issues = [item for item in report.get("issues", []) if isinstance(item, str)]

    if file_kind == CaseFileKind.SCAN:
        warnings = [item for item in issues if item in SCAN_REVIEW_WARNINGS]
        blocking_issues = [item for item in issues if item not in SCAN_REVIEW_WARNINGS]
        policy = "scan_reviewable"
    else:
        warnings = []
        blocking_issues = issues
        policy = "design_strict"

    report.update(
        {
            "validation_policy": policy,
            "warnings": warnings,
            "blocking_issues": blocking_issues,
        }
    )
    status = (
        MeshValidationStatus.INVALID
        if blocking_issues
        else MeshValidationStatus.VALID
    )
    return MeshInspectionResult(status=status, report=report)
