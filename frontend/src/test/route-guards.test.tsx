import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { ManagementReadRoute, ProtectedRoute, ReportsRoute } from "../auth/RouteGuards";
import type { CurrentUser } from "../types/auth";

const baseUser: CurrentUser = {
  id: "9b2b1354-2454-4196-859c-daa00f27cf3e",
  email: "manager@example.test",
  full_name: "Klinik Yöneticisi",
  global_roles: [],
  clinic_roles: [{
    clinic_id: "9acfa1ce-cb10-4e29-9bb3-aebdd62f823f",
    role: "clinic_manager",
  }],
  preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
};

function authValue(overrides: Partial<AuthContextValue>): AuthContextValue {
  return {
    status: "authenticated",
    user: baseUser,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    changePassword: vi.fn().mockResolvedValue(undefined),
    retrySession: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

afterEach(cleanup);

it("oturum servisi erişilemiyorsa çıkışa yönlendirmek yerine yeniden deneme sunar", async () => {
  const retrySession = vi.fn().mockResolvedValue(undefined);
  render(
    <MemoryRouter initialEntries={["/"]}>
      <AuthContext.Provider value={authValue({ status: "unavailable", user: null, retrySession })}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<p>Korunan içerik</p>} />
          </Route>
          <Route path="/giris" element={<p>Giriş</p>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "Oturum doğrulanamadı" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Yeniden dene" }));
  expect(retrySession).toHaveBeenCalledOnce();
  expect(screen.queryByText("Giriş")).not.toBeInTheDocument();
});

it("klinik yöneticisinin salt okunur yönetim rotasına girmesine izin verir", () => {
  render(
    <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
      <AuthContext.Provider value={authValue({})}>
        <Routes>
          <Route element={<ManagementReadRoute />}>
            <Route path="/yonetim/kullanicilar" element={<p>Klinik personeli</p>} />
          </Route>
          <Route path="/yetkisiz" element={<p>Yetkisiz</p>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );

  expect(screen.getByText("Klinik personeli")).toBeInTheDocument();
  expect(screen.queryByText("Yetkisiz")).not.toBeInTheDocument();
});

it("rapor rotasını yalnızca yönetim rollerine açar", () => {
  const dentist: CurrentUser = {
    ...baseUser,
    clinic_roles: [{ ...baseUser.clinic_roles[0], role: "dentist" }],
  };
  const { unmount } = render(
    <MemoryRouter initialEntries={["/raporlar"]}>
      <AuthContext.Provider value={authValue({ user: dentist })}>
        <Routes>
          <Route element={<ReportsRoute />}>
            <Route path="/raporlar" element={<p>Rapor içeriği</p>} />
          </Route>
          <Route path="/yetkisiz" element={<p>Yetkisiz</p>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );

  expect(screen.getByText("Yetkisiz")).toBeInTheDocument();
  unmount();

  render(
    <MemoryRouter initialEntries={["/raporlar"]}>
      <AuthContext.Provider value={authValue({
        user: {
          ...baseUser,
          clinic_roles: [{ ...baseUser.clinic_roles[0], role: "managing_dentist" }],
        },
      })}>
        <Routes>
          <Route element={<ReportsRoute />}>
            <Route path="/raporlar" element={<p>Rapor içeriği</p>} />
          </Route>
          <Route path="/yetkisiz" element={<p>Yetkisiz</p>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );

  expect(screen.getByText("Rapor içeriği")).toBeInTheDocument();
});
