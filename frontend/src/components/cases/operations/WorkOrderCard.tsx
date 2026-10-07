import { usePrintDocument } from "../../../hooks/usePrintDocument";
import { loadBarcodeRenderer } from "../../../lib/barcode-loader";
import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";
import { PrintPortal } from "../../printing/PrintPortal";
import { CaseLabelDocument } from "./CaseLabelDocument";
import { WorkOrderDocument } from "./WorkOrderDocument";

interface Props {
  dentalCase: DentalCase;
  productionRun: ProductionRun;
  canPrintLabel?: boolean;
}

export function WorkOrderCard({ dentalCase, productionRun, canPrintLabel = false }: Props) {
  const workOrder = usePrintDocument();
  const label = usePrintDocument("printing-label");

  async function printLabel() {
    await loadBarcodeRenderer();
    label.print();
  }

  return (
    <>
      <WorkOrderDocument
        dentalCase={dentalCase}
        productionRun={productionRun}
        onPrint={workOrder.print}
        onPrintLabel={canPrintLabel ? () => void printLabel() : undefined}
      />
      {workOrder.isPrinting && (
        <PrintPortal>
          <WorkOrderDocument dentalCase={dentalCase} productionRun={productionRun} />
        </PrintPortal>
      )}
      {label.isPrinting && (
        <PrintPortal>
          <CaseLabelDocument dentalCase={dentalCase} productionRun={productionRun} />
        </PrintPortal>
      )}
    </>
  );
}
