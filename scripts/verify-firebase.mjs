import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const isWindows = process.platform === "win32";
const firebaseCli = fileURLToPath(
  new URL("../node_modules/firebase-tools/lib/bin/firebase.js", import.meta.url),
);
const python = isWindows
  ? "backend\\.venv\\Scripts\\python.exe"
  : "python";
const testCommand = [
  python,
  "-m pytest",
  "-c backend/pyproject.toml",
  "backend/tests/integration/test_firebase_emulator.py",
].join(" ");

const child = spawn(
  process.execPath,
  [
    firebaseCli,
    "emulators:exec",
    "--only",
    "auth",
    "--project",
    "dentalapp-7b131",
    testCommand,
  ],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      FIREBASE_PROJECT_ID: "dentalapp-7b131",
      FIREBASE_USE_EMULATOR: "true",
      RUN_DATABASE_INTEGRATION_TESTS: "1",
      RUN_FIREBASE_EMULATOR_TESTS: "1",
    },
  },
);

child.on("error", (error) => {
  process.stderr.write(`Firebase doğrulaması başlatılamadı: ${error.message}\n`);
  process.exitCode = 1;
});

child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
