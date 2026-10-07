interface BarcodeOptions {
  format: string;
  displayValue: boolean;
  width: number;
  height: number;
  margin: number;
  background: string;
  lineColor: string;
}

type BarcodeRenderer = (
  element: SVGSVGElement,
  value: string,
  options: BarcodeOptions,
) => void;

let rendererPromise: Promise<BarcodeRenderer> | null = null;

export function loadBarcodeRenderer(): Promise<BarcodeRenderer> {
  rendererPromise ??= import("jsbarcode").then((loaded) => {
    const module = loaded as unknown as { default?: BarcodeRenderer };
    return module.default ?? (loaded as unknown as BarcodeRenderer);
  });
  return rendererPromise;
}
