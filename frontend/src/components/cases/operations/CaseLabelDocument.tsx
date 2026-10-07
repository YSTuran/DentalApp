import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";
import { BarcodeGraphic } from "../../printing/BarcodeGraphic";

interface Props {
  dentalCase: DentalCase;
  productionRun: ProductionRun;
}

export function CaseLabelDocument({ dentalCase, productionRun }: Props) {
  return (
    <section className="case-label-document" aria-label="Vaka üretim etiketi">
      <header>
        <strong>DentalApp</strong>
        <span>{productionRun.work_order_number}</span>
      </header>
      <div className="case-label-barcode">
        <BarcodeGraphic value={dentalCase.case_number} />
        <strong>{dentalCase.case_number}</strong>
      </div>
      <dl>
        <div><dt>Klinik</dt><dd>{dentalCase.clinic_name}</dd></div>
        <div><dt>Aparey</dt><dd>{dentalCase.details.appliance_type ?? "—"}</dd></div>
        <div><dt>Üretim</dt><dd>Deneme {productionRun.attempt_number}</dd></div>
        <div><dt>Malzeme</dt><dd>{dentalCase.details.material ?? "—"}</dd></div>
      </dl>
      <small>DEMO · Hasta adı içermez</small>
    </section>
  );
}
