import type { ReactNode } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { LoginPage } from "../pages/LoginPage";
import { SettingsPage } from "../pages/SettingsPage";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { CurrentUser } from "../types/auth";

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

const preferenceMocks = vi.hoisted(() => ({
  updateThemePreferences: vi.fn(),
}));

vi.mock("../lib/preferences-api", () => preferenceMocks);

function authValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    status: "authenticated",
    user: currentUser,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    changePassword: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function renderWithAuth(component: ReactNode, value: AuthContextValue) {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <ThemeProvider>{component}</ThemeProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  preferenceMocks.updateThemePreferences.mockImplementation(async (update) => ({
    ...currentUser.preferences,
    ...update,
  }));
});

describe("hesap ekranları", () => {
  it("girişte oturumu açık tut seçimini kimlik akışına iletir", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderWithAuth(<LoginPage />, authValue({ status: "unauthenticated", user: null, login }));

    await user.type(screen.getByLabelText("E-posta"), "Admin@Example.Test");
    await user.type(screen.getByLabelText("Parola"), "secret-password");
    await user.click(screen.getByLabelText("Oturumu açık tut"));
    await user.click(screen.getByRole("button", { name: "Giriş yap" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith(
        "admin@example.test",
        "secret-password",
        true,
      );
    });
  });

  it("parolayı değiştirmeden önce açık onay ister", async () => {
    const changePassword = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderWithAuth(<SettingsPage />, authValue({ changePassword }));

    await user.type(screen.getByLabelText("Eski parola"), "old-password");
    await user.type(screen.getByLabelText("Yeni parola"), "new-password-123");
    await user.type(screen.getByLabelText("Yeni parola tekrar"), "new-password-123");
    await user.click(screen.getByRole("button", { name: "Parolayı değiştir" }));

    expect(changePassword).not.toHaveBeenCalled();
    expect(
      screen.getByRole("alertdialog", {
        name: "Parola değişikliğini onaylıyor musunuz?",
      }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Evet, değiştir" }));
    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith("old-password", "new-password-123");
    });
  });

  it("tema seçimini hemen uygular ve hesap tercihine kaydeder", async () => {
    const user = userEvent.setup();
    renderWithAuth(<SettingsPage />, authValue());

    await user.click(screen.getByRole("radio", { name: /Karanlık/ }));

    await waitFor(() => {
      expect(preferenceMocks.updateThemePreferences).toHaveBeenCalledWith({
        theme_mode: "dark",
      });
      expect(document.documentElement.dataset.mode).toBe("dark");
    });
  });

  it("yeni renk paletini hemen uygular ve hesap tercihine kaydeder", async () => {
    const user = userEvent.setup();
    renderWithAuth(<SettingsPage />, authValue());

    await user.click(screen.getByRole("radio", { name: /Arktik laboratuvar/ }));

    await waitFor(() => {
      expect(preferenceMocks.updateThemePreferences).toHaveBeenCalledWith({
        color_palette: "arctic",
      });
      expect(document.documentElement.dataset.palette).toBe("arctic");
    });
  });
});

