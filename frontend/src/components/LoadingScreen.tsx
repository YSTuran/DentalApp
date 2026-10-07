interface Props {
  message?: string;
}

export function LoadingScreen({ message = "Oturum kontrol ediliyor…" }: Props) {
  return (
    <main className="loading-screen" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <p>{message}</p>
    </main>
  );
}
