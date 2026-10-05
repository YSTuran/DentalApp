import { formatDate } from "../../../lib/case-format";
import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";

interface Props {
  dentalCase: DentalCase;
  productionRun: ProductionRun;
}

export function WorkOrderCard({ dentalCase, productionRun }: Props) {
  const design = dentalCase.file_versions.find(
    (file) => file.id === productionRun.design_file_version_id,
  );

  return (
    <section className="work-order-print" aria-label="Üretim iş emri">
      <div className="work-order-heading">
        <div><span>İŞ EMRİ</span><strong>{productionRun.work_order_number}</strong></div>
        <button className="secondary-button compact-button no-print" type="button" onClick={() => window.print()}>Yazdır</button>
      </div>
      <dl>
        <div><dt>Vaka</dt><dd>{dentalCase.case_number}</dd></div>
        <div><dt>Hasta kodu</dt><dd>{dentalCase.patient_code ?? "—"}</dd></div>
        <div><dt>Klinik</dt><dd>{dentalCase.clinic_name}</dd></div>
        <div><dt>Üretim</dt><dd>Deneme {productionRun.attempt_number}</dd></div>
        <div><dt>Tasarım</dt><dd>{design ? `v${design.version_number}` : "—"}</dd></div>
        <div><dt>Aparey</dt><dd>{dentalCase.details.appliance_type ?? "—"}</dd></div>
        <div><dt>Malzeme</dt><dd>{dentalCase.details.material ?? "—"}</dd></div>
        <div><dt>Dişler</dt><dd>{dentalCase.details.tooth_numbers.join(", ") || "—"}</dd></div>
        <div><dt>Başlangıç</dt><dd>{formatDate(productionRun.started_at)}</dd></div>
      </dl>
      {productionRun.notes && <p><strong>Not:</strong> {productionRun.notes}</p>}
    </section>
  );
}
