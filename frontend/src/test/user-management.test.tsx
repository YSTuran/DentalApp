import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { listClinics } from "../lib/clinics-api";
import { changeRoleAssignment, listUsers } from "../lib/users-api";
import { UsersPage } from "../pages/UsersPage";
import type { CurrentUser } from "../types/auth";

vi.mock("../lib/clinics-api", () => ({
  listClinics: vi.fn(),
}));

vi.mock("../lib/users-api", () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  changeRoleAssignment: vi.fn(),
  changeUserStatus: vi.fn(),
  userErrorMessage: vi.fn(() => "İşlem tamamlanamadı."),
}));

const currentUser: CurrentUser = {
  id: "9b2b1354-2454-4196-859c-daa00f27cf3e",
  email: "admin@example.test",
  full_name: "Demo Admin",
  global_roles: ["system_admin"],
  clinic_roles: [],
  preferences: {
    theme_mode: "system",
    color_palette: "default",
    updated_at: null,
  },
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
    vi.clearAllMocks();
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

  it("aktif rolü ve kliniği tek işlemle değiştirebilir", async () => {
    const clinicA = {
      id: "9acfa1ce-cb10-4e29-9bb3-aebdd62f823f",
      code: "K001",
      name: "Birinci Klinik",
      address: null,
      phone: null,
      is_active: true,
      created_at: "2026-09-28T10:00:00Z",
      updated_at: "2026-09-28T10:00:00Z",
    };
    const clinicB = {
      ...clinicA,
      id: "15b403b9-079b-422d-b666-c3333789eb83",
      code: "K002",
      name: "İkinci Klinik",
    };
    const assignmentId = "654925b2-ab70-40e5-9e7c-d7fda9a5789a";
    const managedUserId = "26ae89c7-8f4a-40f9-8502-8def51e134fd";
    vi.mocked(listClinics).mockResolvedValue({
      items: [clinicA, clinicB],
      total: 2,
      limit: 100,
      offset: 0,
    });
    vi.mocked(listUsers).mockResolvedValue({
      items: [
        {
          id: managedUserId,
          email: "manager@example.test",
          full_name: "Demo Yönetici Hekim",
          is_active: true,
          created_at: "2026-09-28T10:00:00Z",
          updated_at: "2026-09-28T10:00:00Z",
          role_assignments: [
            {
              id: assignmentId,
              role: "managing_dentist",
              clinic_id: clinicA.id,
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
    vi.mocked(changeRoleAssignment).mockResolvedValue({
      id: "0cd987e0-44f8-4906-a6ac-99e7a70d1417",
      role: "dentist",
      clinic_id: clinicB.id,
      is_active: true,
      created_at: "2026-09-28T10:05:00Z",
      updated_at: "2026-09-28T10:05:00Z",
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
        <AuthContext.Provider value={authValue}>
          <UsersPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Demo Yönetici Hekim")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Rol/Klinik düzenle" }));
    const dialog = screen.getByRole("dialog", { name: "Rol ve klinik düzenle" });
    await user.selectOptions(within(dialog).getByLabelText("Yeni rol"), "dentist");
    await user.selectOptions(within(dialog).getByLabelText("Yeni klinik"), clinicB.id);
    await user.type(
      within(dialog).getByLabelText("Değişiklik gerekçesi"),
      "Görev yeri değişti",
    );
    await user.click(within(dialog).getByRole("button", { name: "Değişikliği uygula" }));

    await waitFor(() => {
      expect(changeRoleAssignment).toHaveBeenCalledWith(managedUserId, assignmentId, {
        role: "dentist",
        clinic_id: clinicB.id,
        reason: "Görev yeri değişti",
      });
    });
  });
});

