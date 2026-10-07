import { useEffect, useRef } from "react";

import { loadBarcodeRenderer } from "../../lib/barcode-loader";

interface Props {
  value: string;
}

export function BarcodeGraphic({ value }: Props) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    let active = true;
    void loadBarcodeRenderer().then((JsBarcode) => {
      if (!active || !ref.current) return;
      JsBarcode(ref.current, value, {
        format: "CODE128",
        displayValue: false,
        width: 1.7,
        height: 48,
        margin: 0,
        background: "#ffffff",
        lineColor: "#000000",
      });
    });
    return () => { active = false; };
  }, [value]);

  return <svg ref={ref} role="img" aria-label={`${value} barkodu`} />;
}
