import { getApp, getApps, initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";

const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "dentalapp-7b131";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? "demo-api-key",
  authDomain:
    import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? `${projectId}.firebaseapp.com`,
  projectId,
  appId: import.meta.env.VITE_FIREBASE_APP_ID ?? "demo-app-id",
};

const firebaseApp = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

export const firebaseAuth = getAuth(firebaseApp);

if (
  import.meta.env.VITE_FIREBASE_USE_EMULATOR !== "false" &&
  firebaseAuth.emulatorConfig === null
) {
  connectAuthEmulator(
    firebaseAuth,
    import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_URL ?? "http://127.0.0.1:9099",
    { disableWarnings: true },
  );
}
