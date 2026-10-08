import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("API istemcisi", () => {
  it("yapılandırılmış backend hatasının kodunu ve ayrıntısını korur", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "case_required_fields_missing",
            fields: ["patient_code", "material"],
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    ));
    const { ApiError, apiRequest } = await import("../lib/api");

    try {
      await apiRequest("/api/cases/example/submit");
      throw new Error("İsteğin hata vermesi bekleniyordu.");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as InstanceType<typeof ApiError>).detail).toBe(
        "case_required_fields_missing",
      );
      expect((error as InstanceType<typeof ApiError>).data).toEqual({
        code: "case_required_fields_missing",
        fields: ["patient_code", "material"],
      });
    }
  });

  it("paralel değişiklik istekleri için tek CSRF anahtarı alır", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/auth/csrf")) {
        return new Response(JSON.stringify({ csrf_token: "shared-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { csrfRequest } = await import("../lib/api");

    await Promise.all([
      csrfRequest("/api/one", { method: "POST" }),
      csrfRequest("/api/two", { method: "POST" }),
    ]);

    const csrfCalls = fetchMock.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/auth/csrf")
    );
    expect(csrfCalls).toHaveLength(1);
  });

  it("geçersiz oturum yanıtını merkezi dinleyicilere bildirir", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "not_authenticated" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    ));
    const { apiRequest, subscribeToSessionInvalidation } = await import("../lib/api");
    const listener = vi.fn();
    const unsubscribe = subscribeToSessionInvalidation(listener);

    await expect(apiRequest("/api/cases")).rejects.toMatchObject({
      status: 401,
      detail: "not_authenticated",
    });
    expect(listener).toHaveBeenCalledOnce();

    unsubscribe();
  });

  it("sıradan yetki reddini oturum kaybı olarak değerlendirmez", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "insufficient_permissions" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    ));
    const { apiRequest, subscribeToSessionInvalidation } = await import("../lib/api");
    const listener = vi.fn();
    subscribeToSessionInvalidation(listener);

    await expect(apiRequest("/api/admin-only")).rejects.toMatchObject({
      status: 403,
      detail: "insufficient_permissions",
    });
    expect(listener).not.toHaveBeenCalled();
  });
});
