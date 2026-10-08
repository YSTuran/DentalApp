import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "../types/auth";

const firebaseMocks = vi.hoisted(() => {
  const firebaseUser = {
    getIdToken: vi.fn(),
  };

  return {
    firebaseUser,
    auth: {
      authStateReady: vi.fn(),
      currentUser: firebaseUser,
    },
    credential: vi.fn(),
    reauthenticateWithCredential: vi.fn(),
    setPersistence: vi.fn(),
    signInWithEmailAndPassword: vi.fn(),
    signOut: vi.fn(),
    updatePassword: vi.fn(),
  };
});

const apiMocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  destroySession: vi.fn(),
  getCurrentUser: vi.fn(),
  recordPasswordChanged: vi.fn(),
  subscribeToSessionInvalidation: vi.fn(),
}));

vi.mock("firebase/auth", () => ({
  browserLocalPersistence: { type: "LOCAL" },
  browserSessionPersistence: { type: "SESSION" },
  EmailAuthProvider: { credential: firebaseMocks.credential },
  reauthenticateWithCredential: firebaseMocks.reauthenticateWithCredential,
  setPersistence: firebaseMocks.setPersistence,
  signInWithEmailAndPassword: firebaseMocks.signInWithEmailAndPassword,
  signOut: firebaseMocks.signOut,
  updatePassword: firebaseMocks.updatePassword,
}));

vi.mock("../lib/firebase", () => ({
  firebaseAuth: firebaseMocks.auth,
}));

vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      public readonly status: number,
      public readonly detail: string,
    ) {
      super(detail);
    }
  },
  ...apiMocks,
}));

import { AuthProvider } from "../auth/AuthProvider";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";

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

function PasswordChangeHarness() {
  const { changePassword, status } = useAuth();
  const [result, setResult] = useState("waiting");

  return (
    <>
      <span>{status}</span>
      <span>{result}</span>
      <button
        type="button"
        onClick={() => {
          void changePassword("old-password", "new-password-123").then(() => {
            setResult("completed");
          });
        }}
      >
        Parolayı güncelle
      </button>
    </>
  );
}

function SessionHarness() {
  const { logout, status, user } = useAuth();

  return (
    <>
      <span>{status}</span>
      <span>{user?.email ?? "no-user"}</span>
      <button type="button" onClick={() => void logout()}>
        Oturumu kapat
      </button>
    </>
  );
}

afterEach(cleanup);

describe("AuthProvider parola değişikliği", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("dentalapp.remember_session", "true");

    firebaseMocks.auth.currentUser = firebaseMocks.firebaseUser;
    firebaseMocks.auth.authStateReady.mockResolvedValue(undefined);
    firebaseMocks.credential.mockReturnValue({ providerId: "password" });
    firebaseMocks.reauthenticateWithCredential.mockResolvedValue(undefined);
    firebaseMocks.signOut.mockResolvedValue(undefined);
    firebaseMocks.updatePassword.mockResolvedValue(undefined);
    firebaseMocks.firebaseUser.getIdToken.mockResolvedValue("fresh-id-token");
    apiMocks.getCurrentUser.mockResolvedValue(currentUser);
    apiMocks.recordPasswordChanged.mockResolvedValue(currentUser);
    apiMocks.subscribeToSessionInvalidation.mockImplementation(() => () => undefined);
  });

  it("yeni ID token ile backend oturumunu yenileyip audit isteği gönderir", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <PasswordChangeHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText("authenticated")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Parolayı güncelle" }));

    expect(await screen.findByText("completed")).toBeInTheDocument();
    expect(firebaseMocks.updatePassword).toHaveBeenCalledWith(
      firebaseMocks.firebaseUser,
      "new-password-123",
    );
    expect(firebaseMocks.firebaseUser.getIdToken).toHaveBeenCalledWith(true);
    await waitFor(() => {
      expect(apiMocks.recordPasswordChanged).toHaveBeenCalledWith(
        "fresh-id-token",
        true,
      );
    });
  });

  it("backend erişilemiyorsa bile Firebase ve yerel oturumu kapatır", async () => {
    const user = userEvent.setup();
    apiMocks.destroySession.mockRejectedValueOnce(new TypeError("network down"));

    render(
      <AuthProvider>
        <SessionHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText(currentUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Oturumu kapat" }));

    expect(await screen.findByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("no-user")).toBeInTheDocument();
    expect(firebaseMocks.signOut).toHaveBeenCalled();
  });

  it("çalışma sırasında geçersizleşen oturumu merkezi bildirimle kapatır", async () => {
    render(
      <AuthProvider>
        <SessionHarness />
      </AuthProvider>,
    );

    expect(await screen.findByText(currentUser.email)).toBeInTheDocument();
    const listener = apiMocks.subscribeToSessionInvalidation.mock.calls[0]?.[0];
    expect(listener).toBeTypeOf("function");

    act(() => listener(new ApiError(401, "not_authenticated")));

    expect(await screen.findByText("unauthenticated")).toBeInTheDocument();
    expect(screen.getByText("no-user")).toBeInTheDocument();
    expect(firebaseMocks.signOut).toHaveBeenCalled();
    expect(window.localStorage.getItem("dentalapp.remember_session")).toBeNull();
  });

  it.each(["account_not_provisioned", "account_inactive"])(
    "%s yanıtını servis kesintisi yerine giriş yapılmamış olarak gösterir",
    async (detail) => {
      apiMocks.getCurrentUser.mockRejectedValueOnce(new ApiError(403, detail));

      render(
        <AuthProvider>
          <SessionHarness />
        </AuthProvider>,
      );

      expect(await screen.findByText("unauthenticated")).toBeInTheDocument();
      expect(screen.getByText("no-user")).toBeInTheDocument();
    },
  );
});
