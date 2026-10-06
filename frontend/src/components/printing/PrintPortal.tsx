import type { ReactNode } from "react";
import { createPortal } from "react-dom";

interface Props {
  children: ReactNode;
}

export function PrintPortal({ children }: Props) {
  return createPortal(<div className="print-root">{children}</div>, document.body);
}
