import { afterEach, expect, it, vi } from "vitest";

import type { AuditEvent } from "../types/audit";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

function auditEvent(id: string): AuditEvent {
  return {
    id,
    action: "case.shipped",
    entity_type: "case",
    entity_id: `case-${id}`,
    actor_user_id: null,
    actor_email: null,
    clinic_id: null,
    reason: null,
    before_data: null,
    after_data: null,
    context: {},
    ip_address: null,
    user_agent: null,
    created_at: "2026-10-06T08:00:00Z",
  };
}

it("PDF için aktif filtreyle eşleşen bütün audit sayfalarını toplar", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({
      items: [auditEvent("one")], total: 2, limit: 100, offset: 0,
    }), { status: 200, headers: { "Content-Type": "application/json" } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      items: [auditEvent("two")], total: 2, limit: 100, offset: 1,
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  const { listAllAuditEvents } = await import("../lib/audit-api");

  const events = await listAllAuditEvents({
    action: "case.shipped",
    createdFrom: "2026-10-01T00:00:00Z",
    limit: 15,
    offset: 30,
  });

  expect(events.map(({ id }) => id)).toEqual(["one", "two"]);
  expect(String(fetchMock.mock.calls[0][0])).toContain("action=case.shipped");
  expect(String(fetchMock.mock.calls[1][0])).toContain("offset=1");
});
