import { FirebaseError } from "firebase/app";
import {
  browserLocalPersistence,
  browserSessionPersistence,
  EmailAuthProvider,
  reauthenticateWithCredential,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
  updatePassword,
} from "firebase/auth";
import { type PropsWithChildren, useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createSession,
  destroySession,
  getCurrentUser,
  recordPasswordChanged,
} from "../lib/api";
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

  const login = useCallback(async (email: string, password: string, rememberMe: boolean) => {
    try {
      await setPersistence(
        firebaseAuth,
        rememberMe ? browserLocalPersistence : browserSessionPersistence,
      );
      const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
      const idToken = await credential.user.getIdToken(true);
      const currentUser = await createSession(idToken, rememberMe);
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      await signOut(firebaseAuth).catch(() => undefined);
      setUser(null);
      setStatus("unauthenticated");
      throw friendlyAuthError(error);
    }
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    if (user === null) {
      throw new Error("Parola değiştirmek için oturum açmalısınız.");
    }

    try {
      await firebaseAuth.authStateReady();
      let firebaseUser = firebaseAuth.currentUser;

      if (firebaseUser === null) {
        const credential = await signInWithEmailAndPassword(
          firebaseAuth,
          user.email,
          currentPassword,
        );
        firebaseUser = credential.user;
      } else {
        const credential = EmailAuthProvider.credential(user.email, currentPassword);
        await reauthenticateWithCredential(firebaseUser, credential);
      }

      await updatePassword(firebaseUser, newPassword);
      await recordPasswordChanged();
    } catch (error) {
      if (error instanceof FirebaseError) {
        const messages: Record<string, string> = {
          "auth/invalid-credential": "Eski parola hatalı.",
          "auth/wrong-password": "Eski parola hatalı.",
          "auth/weak-password": "Yeni parola Firebase güvenlik koşullarını karşılamıyor.",
          "auth/requires-recent-login": "Güvenlik nedeniyle yeniden giriş yapmanız gerekiyor.",
          "auth/network-request-failed": "Firebase Auth Emulator'a ulaşılamıyor.",
          "auth/too-many-requests": "Çok fazla deneme yapıldı. Biraz sonra tekrar deneyin.",
        };
        throw new Error(messages[error.code] ?? "Parola değiştirilemedi.", {
          cause: error,
        });
      }
      if (error instanceof ApiError) {
        throw new Error(
          "Parola Firebase üzerinde değiştirildi ancak audit kaydı doğrulanamadı.",
          { cause: error },
        );
      }
      throw error instanceof Error ? error : new Error("Parola değiştirilemedi.");
    }
  }, [user]);

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
    () => ({ status, user, login, logout, changePassword }),
    [changePassword, login, logout, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
