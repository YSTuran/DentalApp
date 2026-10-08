import { usePrintDocument } from "../../../hooks/usePrintDocument";
import { loadBarcodeRenderer } from "../../../lib/barcode-loader";
import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";
import { PrintPortal } from "../../printing/PrintPortal";
import { WorkOrderDocument } from "./WorkOrderDocument";

interface Props {
  dentalCase: DentalCase;
  productionRun: ProductionRun;
  includeBarcode?: boolean;
}

export function WorkOrderCard({
  dentalCase,
  productionRun,
  includeBarcode = false,
}: Props) {
  const workOrder = usePrintDocument();

  async function printWorkOrder() {
    if (includeBarcode) await loadBarcodeRenderer();
    workOrder.print();
  }

  return (
    <>
      <WorkOrderDocument
        dentalCase={dentalCase}
        productionRun={productionRun}
        includeBarcode={includeBarcode}
        onPrint={() => void printWorkOrder()}
      />
      {workOrder.isPrinting && (
        <PrintPortal>
          <WorkOrderDocument
            dentalCase={dentalCase}
            productionRun={productionRun}
            includeBarcode={includeBarcode}
          />
        </PrintPortal>
      )}
    </>
  );
}
