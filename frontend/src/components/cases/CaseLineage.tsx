import { Link } from "react-router-dom";

import type { DentalCase } from "../../types/case";

interface Props {
  dentalCase: DentalCase;
}

export function CaseLineage({ dentalCase }: Props) {
  if (!dentalCase.reproduction_source_case_id && !dentalCase.reproduction_case_id) {
    return null;
  }

  return (
    <div className="case-lineage" role="status">
      {dentalCase.reproduction_source_case_id && (
        <span>
          Kaynak iade vakası:{" "}
          <Link to={`/vakalar/${dentalCase.reproduction_source_case_id}`}>
            {dentalCase.reproduction_source_case_number}
          </Link>
        </span>
      )}
      {dentalCase.reproduction_case_id && (
        <span>
          Oluşturulan yeniden üretim vakası:{" "}
          <Link to={`/vakalar/${dentalCase.reproduction_case_id}`}>
            {dentalCase.reproduction_case_number}
          </Link>
        </span>
      )}
    </div>
  );
}
