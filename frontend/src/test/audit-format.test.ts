import { describe, expect, it } from "vitest";

import { formatAuditReason } from "../lib/audit-format";

describe("audit gerekçe gösterimi", () => {
  it.each([null, undefined, "", "   "])("boş gerekçeyi tire olarak gösterir", (reason) => {
    expect(formatAuditReason(reason)).toBe("-");
  });

  it("mevcut gerekçenin çevresindeki boşlukları temizler", () => {
    expect(formatAuditReason("  Görev yeri değişti  ")).toBe("Görev yeri değişti");
  });
});
