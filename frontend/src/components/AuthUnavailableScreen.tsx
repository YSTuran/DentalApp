interface AuthUnavailableScreenProps {
  onRetry: () => Promise<void>;
  onLogout: () => Promise<void>;
}

export function AuthUnavailableScreen({ onRetry, onLogout }: AuthUnavailableScreenProps) {
  return (
    <main className="loading-screen" role="alert">
      <section className="service-unavailable-card">
        <p className="eyebrow">Bağlantı sorunu</p>
        <h1>Oturum doğrulanamadı</h1>
        <p>
          FastAPI veya Firebase servisine şu anda ulaşılamıyor. Oturumunuz sonlandırılmadı;
          servisleri kontrol edip yeniden deneyebilirsiniz.
        </p>
        <div className="button-row">
          <button type="button" className="primary-button" onClick={() => void onRetry()}>
            Yeniden dene
          </button>
          <button type="button" className="secondary-button" onClick={() => void onLogout()}>
            Bu cihazdaki oturumu kapat
          </button>
        </div>
      </section>
    </main>
  );
}
