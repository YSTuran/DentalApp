import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { listClinics } from "../lib/clinics-api";
import { listUsers } from "../lib/users-api";
import { UsersPage } from "../pages/UsersPage";
import type { CurrentUser } from "../types/auth";

vi.mock("../lib/clinics-api", () => ({
  listClinics: vi.fn(),
}));

vi.mock("../lib/users-api", () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  changeUserStatus: vi.fn(),
  userErrorMessage: vi.fn(() => "İşlem tamamlanamadı."),
}));

const currentUser: CurrentUser = {
  id: "9b2b1354-2454-4196-859c-daa00f27cf3e",
  email: "admin@example.test",
  full_name: "Demo Admin",
  global_roles: ["system_admin"],
  clinic_roles: [],
};

const authValue: AuthContextValue = {
  status: "authenticated",
  user: currentUser,
  login: vi.fn().mockResolvedValue(undefined),
  logout: vi.fn().mockResolvedValue(undefined),
  changePassword: vi.fn().mockResolvedValue(undefined),
};

afterEach(cleanup);

describe("kullanıcı yönetimi güvenlik davranışları", () => {
  beforeEach(() => {
    vi.mocked(listClinics).mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 });
    vi.mocked(listUsers).mockResolvedValue({
      items: [
        {
          id: currentUser.id,
          email: currentUser.email,
          full_name: currentUser.full_name,
          is_active: true,
          created_at: "2026-09-28T10:00:00Z",
          updated_at: "2026-09-28T10:00:00Z",
          role_assignments: [
            {
              id: "4135d459-986e-41e3-9766-f0520ed09fc8",
              role: "system_admin",
              clinic_id: null,
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });
  });

  it("oturumdaki admin için pasifleştirme eylemi göstermez", async () => {
    render(
      <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
        <AuthContext.Provider value={authValue}>
          <UsersPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Mevcut hesap")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pasife al" })).not.toBeInTheDocument();
  });

  it("yeni kullanıcı formunda sistem yöneticisi rolünü sunmaz", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
        <AuthContext.Provider value={authValue}>
          <UsersPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(listUsers).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "+ Yeni kullanıcı" }));

    const dialog = screen.getByRole("dialog", { name: "Yeni kullanıcı" });
    expect(
      within(dialog).queryByRole("option", { name: "Sistem yöneticisi" }),
    ).not.toBeInTheDocument();
  });
});

