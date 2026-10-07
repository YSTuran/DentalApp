import { useCallback, useEffect, useState } from "react";

export function usePrintDocument(bodyClass = "printing-report") {
  const [isPrinting, setIsPrinting] = useState(false);

  useEffect(() => {
    if (!isPrinting) return;

    let finished = false;
    let fallbackTimer: number | undefined;
    const finish = () => {
      if (finished) return;
      finished = true;
      document.body.classList.remove(bodyClass);
      setIsPrinting(false);
    };

    document.body.classList.add(bodyClass);
    window.addEventListener("afterprint", finish, { once: true });
    const printTimer = window.setTimeout(() => {
      window.print();
      fallbackTimer = window.setTimeout(finish, 1000);
    }, 0);

    return () => {
      window.clearTimeout(printTimer);
      if (fallbackTimer !== undefined) window.clearTimeout(fallbackTimer);
      window.removeEventListener("afterprint", finish);
      document.body.classList.remove(bodyClass);
    };
  }, [bodyClass, isPrinting]);

  const print = useCallback(() => setIsPrinting(true), []);
  return { isPrinting, print };
}
