import { FirebaseError } from "firebase/app";
import {
  browserLocalPersistence,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import { type PropsWithChildren, useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, createSession, destroySession, getCurrentUser } from "../lib/api";
import { firebaseAuth } from "../lib/firebase";
import type { CurrentUser } from "../types/auth";
import { AuthContext, type AuthStatus } from "./AuthContext";

function friendlyAuthError(error: unknown): Error {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      account_inactive: "Hesabınız pasif durumda. Sistem yöneticisiyle iletişime geçin.",
      account_not_provisioned: "Bu Firebase hesabı DentalApp kullanıcısı olarak tanımlanmamış.",
      csrf_validation_failed: "Güvenlik doğrulaması başarısız oldu. Sayfayı yenileyip tekrar deneyin.",
      authentication_service_unavailable: "Kimlik doğrulama servisine şu anda ulaşılamıyor.",
    };

    return new Error(messages[error.detail] ?? "Oturum oluşturulamadı.");
  }

  if (error instanceof FirebaseError) {
    const messages: Record<string, string> = {
      "auth/invalid-credential": "E-posta veya parola hatalı.",
      "auth/invalid-email": "Geçerli bir e-posta adresi girin.",
      "auth/network-request-failed": "Firebase Auth Emulator'a ulaşılamıyor.",
      "auth/too-many-requests": "Çok fazla başarısız deneme yapıldı. Biraz sonra tekrar deneyin.",
      "auth/user-disabled": "Bu Firebase hesabı devre dışı bırakılmış.",
    };

    return new Error(messages[error.code] ?? "Firebase ile giriş yapılamadı.");
  }

  if (error instanceof TypeError) {
    return new Error("FastAPI sunucusuna ulaşılamıyor.");
  }

  return error instanceof Error ? error : new Error("Beklenmeyen bir hata oluştu.");
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setStatus("authenticated");
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        if (!(error instanceof ApiError) || error.status !== 401) {
          console.error("Oturum bilgisi alınamadı", error);
        }
        setUser(null);
        setStatus("unauthenticated");
      });

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      await setPersistence(firebaseAuth, browserLocalPersistence);
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      const idToken = await credential.user.getIdToken(true);
      const currentUser = await createSession(idToken);
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      await signOut(firebaseAuth).catch(() => undefined);
      setUser(null);
      setStatus("unauthenticated");
      throw friendlyAuthError(error);
    }
  }, []);

  const logout = useCallback(async () => {
    await destroySession();
    try {
      await signOut(firebaseAuth);
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [login, logout, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
