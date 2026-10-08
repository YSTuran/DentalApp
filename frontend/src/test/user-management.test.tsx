import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { listClinics } from "../lib/clinics-api";
import { addClinicAssignment, changeRoleAssignment, listUsers } from "../lib/users-api";
import { UsersPage } from "../pages/UsersPage";
import type { CurrentUser } from "../types/auth";

vi.mock("../lib/clinics-api", () => ({
  listClinics: vi.fn(),
}));

vi.mock("../lib/users-api", () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  addClinicAssignment: vi.fn(),
  changeRoleAssignment: vi.fn(),
  changeClinicAssignmentStatus: vi.fn(),
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
  retrySession: vi.fn().mockResolvedValue(undefined),
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
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
          clinic_assignments: [],
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
    expect(screen.queryByRole("link", { name: "Raporlar" })).not.toBeInTheDocument();
  });

  it("kullanıcı listesinde yalnızca aktif rol atamalarını gösterir", async () => {
    const existingUser = (await listUsers({})).items[0];
    vi.mocked(listUsers).mockResolvedValue({
      items: [{
        ...existingUser,
        role_assignments: [
          ...existingUser.role_assignments,
          {
            id: "bd128125-8628-4234-a53e-0898e69d6a91",
            role: "dentist",
            is_active: false,
            created_at: "2026-09-27T10:00:00Z",
            updated_at: "2026-09-28T10:00:00Z",
          },
        ],
      }],
      total: 1,
      limit: 10,
      offset: 0,
    });

    render(
      <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
        <AuthContext.Provider value={authValue}>
          <UsersPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    const userRow = (await screen.findByText("Demo Admin")).closest("tr");
    expect(userRow).not.toBeNull();
    expect(within(userRow!).getByText("Sistem yöneticisi")).toBeInTheDocument();
    expect(within(userRow!).queryByText("Hekim")).not.toBeInTheDocument();
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

  it("rolü ve klinik atamasını birbirinden bağımsız yönetir", async () => {
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
    const clinicManagerId = "18ca33df-5032-47cf-bf0e-687249d4035f";
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
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
          clinic_assignments: [
            {
              id: "f7b1f765-009b-4f3f-b5b9-1fd02424bd72",
              clinic_id: clinicA.id,
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
        },
        {
          id: clinicManagerId,
          email: "clinic-manager@example.test",
          full_name: "Demo Klinik Yöneticisi",
          is_active: true,
          created_at: "2026-09-28T10:00:00Z",
          updated_at: "2026-09-28T10:00:00Z",
          role_assignments: [
            {
              id: "335ac12b-15f3-4679-a270-48be854854f6",
              role: "clinic_manager",
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
          clinic_assignments: [
            {
              id: "28213c6e-8d58-4cb3-ab7b-88952895c507",
              clinic_id: clinicA.id,
              is_active: true,
              created_at: "2026-09-28T10:00:00Z",
              updated_at: "2026-09-28T10:00:00Z",
            },
          ],
        },
      ],
      total: 2,
      limit: 10,
      offset: 0,
    });
    vi.mocked(changeRoleAssignment).mockResolvedValue({
      id: "0cd987e0-44f8-4906-a6ac-99e7a70d1417",
      role: "dentist",
      is_active: true,
      created_at: "2026-09-28T10:05:00Z",
      updated_at: "2026-09-28T10:05:00Z",
    });
    vi.mocked(addClinicAssignment).mockResolvedValue({
      id: "7953100d-92f5-40e3-89af-1a65e4518787",
      clinic_id: clinicB.id,
      is_active: true,
      created_at: "2026-09-28T10:06:00Z",
      updated_at: "2026-09-28T10:06:00Z",
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
    const doctorRow = screen.getByText("Demo Yönetici Hekim").closest("tr");
    expect(doctorRow).not.toBeNull();
    await user.click(within(doctorRow!).getByRole("button", { name: "Rolü düzenle" }));
    const dialog = screen.getByRole("dialog", { name: "Rolü düzenle" });
    await user.selectOptions(within(dialog).getByLabelText("Yeni rol"), "dentist");
    await user.type(
      within(dialog).getByLabelText("Değişiklik gerekçesi"),
      "Görev yeri değişti",
    );
    await user.click(within(dialog).getByRole("button", { name: "Değişikliği uygula" }));

    await waitFor(() => {
      expect(changeRoleAssignment).toHaveBeenCalledWith(managedUserId, assignmentId, {
        role: "dentist",
        reason: "Görev yeri değişti",
      });
    });

    const managerRow = screen.getByText("Demo Klinik Yöneticisi").closest("tr");
    expect(managerRow).not.toBeNull();
    await user.click(within(managerRow!).getByRole("button", { name: "Klinik ekle" }));
    const addDialog = screen.getByRole("dialog", { name: "Klinik ekle" });
    await user.selectOptions(within(addDialog).getByLabelText("Yeni klinik"), clinicB.id);
    await user.type(within(addDialog).getByLabelText(/Atama gerekçesi/), "İkinci şube");
    await user.click(within(addDialog).getByRole("button", { name: "Kliniği ekle" }));

    await waitFor(() => {
      expect(addClinicAssignment).toHaveBeenCalledWith(clinicManagerId, {
        clinic_id: clinicB.id,
        reason: "İkinci şube",
      });
    });
  });

  it("klinik yöneticisine kendi kapsamındaki hekim ve asistanları salt okunur gösterir", async () => {
    const clinicId = "9acfa1ce-cb10-4e29-9bb3-aebdd62f823f";
    const managerUser: CurrentUser = {
      ...currentUser,
      global_roles: [],
      clinic_roles: [{ clinic_id: clinicId, role: "clinic_manager" }],
    };
    vi.mocked(listClinics).mockResolvedValue({
      items: [{
        id: clinicId,
        code: "K001",
        name: "Birinci Klinik",
        address: null,
        phone: null,
        is_active: true,
        created_at: "2026-09-28T10:00:00Z",
        updated_at: "2026-09-28T10:00:00Z",
      }],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(listUsers).mockResolvedValue({
      items: [
        {
          id: "26ae89c7-8f4a-40f9-8502-8def51e134fd",
          email: "doctor@example.test",
          full_name: "Demo Hekim",
          is_active: true,
          created_at: "2026-09-28T10:00:00Z",
          updated_at: "2026-09-28T10:00:00Z",
          role_assignments: [{
            id: "654925b2-ab70-40e5-9e7c-d7fda9a5789a",
            role: "dentist",
            is_active: true,
            created_at: "2026-09-28T10:00:00Z",
            updated_at: "2026-09-28T10:00:00Z",
          }],
          clinic_assignments: [{
            id: "b6682e26-7f92-4d10-a05a-eb2c5ea4ff6c",
            clinic_id: clinicId,
            is_active: true,
            created_at: "2026-09-28T10:00:00Z",
            updated_at: "2026-09-28T10:00:00Z",
          }],
        },
        {
          id: "45e6673d-5e84-43df-87ce-fd20ef9f7a84",
          email: "assistant@example.test",
          full_name: "Demo Asistan",
          is_active: true,
          created_at: "2026-09-28T10:00:00Z",
          updated_at: "2026-09-28T10:00:00Z",
          role_assignments: [{
            id: "ae032f35-f105-42e9-b933-a94a4d550026",
            role: "clinic_staff",
            is_active: true,
            created_at: "2026-09-28T10:00:00Z",
            updated_at: "2026-09-28T10:00:00Z",
          }],
          clinic_assignments: [{
            id: "465c585b-7e98-4dc2-a073-54081614b118",
            clinic_id: clinicId,
            is_active: true,
            created_at: "2026-09-28T10:00:00Z",
            updated_at: "2026-09-28T10:00:00Z",
          }],
        },
      ],
      total: 2,
      limit: 10,
      offset: 0,
    });

    render(
      <MemoryRouter initialEntries={["/yonetim/kullanicilar"]}>
        <AuthContext.Provider value={{ ...authValue, user: managerUser }}>
          <UsersPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Demo Hekim")).toBeInTheDocument();
    expect(screen.getByText("Demo Asistan")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Klinik personeli / asistan" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "+ Yeni kullanıcı" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rolü düzenle" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pasife al" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Sistem yöneticisi" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Raporlar" })).not.toBeInTheDocument();
  });
});

