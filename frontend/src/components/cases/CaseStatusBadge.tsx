import { caseStatusLabels, meshStatusLabels } from "../../lib/case-format";
import type { CaseStatus, MeshStatus } from "../../types/case";

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return <span className={`case-status case-status-${status}`}>{caseStatusLabels[status]}</span>;
}

export function MeshStatusBadge({ status }: { status: MeshStatus }) {
  return <span className={`mesh-status mesh-status-${status}`}>{meshStatusLabels[status]}</span>;
}
