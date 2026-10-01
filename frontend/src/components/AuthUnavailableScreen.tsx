interface AuthUnavailableScreenProps {
  onRetry: () => Promise<void>;
}

export function AuthUnavailableScreen({ onRetry }: AuthUnavailableScreenProps) {
  return (
    <main className="loading-screen" role="alert">
      <section className="service-unavailable-card">
        <p className="eyebrow">Bağlantı sorunu</p>
        <h1>Oturum doğrulanamadı</h1>
        <p>
          FastAPI veya Firebase servisine şu anda ulaşılamıyor. Oturumunuz sonlandırılmadı;
          servisleri kontrol edip yeniden deneyebilirsiniz.
        </p>
        <button type="button" className="primary-button" onClick={() => void onRetry()}>
          Yeniden dene
        </button>
      </section>
    </main>
  );
}
