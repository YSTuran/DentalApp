export function LoadingScreen() {
  return (
    <main className="loading-screen" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <p>Oturum kontrol ediliyor…</p>
    </main>
  );
}
