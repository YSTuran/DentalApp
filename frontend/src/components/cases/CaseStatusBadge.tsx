import { caseStatusLabels, meshStatusLabels } from "../../lib/case-format";
import type { CaseStatus, MeshStatus } from "../../types/case";

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return <span className={`case-status case-status-${status}`}>{caseStatusLabels[status]}</span>;
}

export function MeshStatusBadge({
  status,
  hasWarnings = false,
}: {
  status: MeshStatus;
  hasWarnings?: boolean;
}) {
  const warning = status === "valid" && hasWarnings;
  return (
    <span className={`mesh-status mesh-status-${warning ? "warning" : status}`}>
      {warning ? "İnceleme uyarısı" : meshStatusLabels[status]}
    </span>
  );
}
