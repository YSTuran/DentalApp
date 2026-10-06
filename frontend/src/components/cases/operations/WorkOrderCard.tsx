import { usePrintDocument } from "../../../hooks/usePrintDocument";
import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";
import { PrintPortal } from "../../printing/PrintPortal";
import { WorkOrderDocument } from "./WorkOrderDocument";

interface Props {
  dentalCase: DentalCase;
  productionRun: ProductionRun;
}

export function WorkOrderCard({ dentalCase, productionRun }: Props) {
  const { isPrinting, print } = usePrintDocument();

  return (
    <>
      <WorkOrderDocument dentalCase={dentalCase} productionRun={productionRun} onPrint={print} />
      {isPrinting && (
        <PrintPortal>
          <WorkOrderDocument dentalCase={dentalCase} productionRun={productionRun} />
        </PrintPortal>
      )}
    </>
  );
}
