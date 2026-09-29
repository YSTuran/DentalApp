import { describe, expect, it } from "vitest";

import { auditToneFor } from "../lib/audit-colors";

describe("audit kayıt renkleri", () => {
  it.each([
    ["auth.session_created", "user", "session"],
    ["account.password_changed", "user", "security"],
    ["clinic.updated", "clinic", "clinic"],
    ["user.updated", "user", "user"],
    ["user.role_changed", "user_role_assignment", "role"],
    ["case.submitted", "case", "case"],
    ["production.started", "production_job", "production"],
    ["shipment.created", "shipment", "delivery"],
    ["unknown.event", "unknown", "system"],
  ])("%s işlemini %s tonu ile sınıflandırır", (action, entityType, tone) => {
    expect(auditToneFor(action, entityType)).toBe(tone);
  });
});
