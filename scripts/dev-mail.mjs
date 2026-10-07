import { spawn } from "node:child_process";

const inboxUrl = "http://localhost:8025";
process.stdout.write(`Test e-posta kutusu: ${inboxUrl}\n`);

const docker = spawn("docker", ["compose", "up", "--no-color", "mailpit"], {
  cwd: new URL("..", import.meta.url),
  stdio: "inherit",
});

docker.on("error", (error) => {
  process.stderr.write(`Mailpit başlatılamadı: ${error.message}\n`);
  process.exitCode = 1;
});

docker.on("exit", (code) => {
  process.exitCode = code ?? 1;
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => docker.kill(signal));
}
