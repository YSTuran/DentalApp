import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login(email.trim().toLowerCase(), password, rememberMe);
      navigate("/", { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Giriş yapılamadı.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-intro" aria-labelledby="product-title">
        <div className="brand-mark" aria-hidden="true">
          D
        </div>
        <p className="eyebrow">KLİNİK · LABORATUVAR</p>
        <h1 id="product-title">DentalApp</h1>
        <p className="auth-intro-copy">
          Dijital vakaları, tasarım onaylarını ve üretim sürecini tek bir güvenli akışta
          yönetin.
        </p>
        <div className="flow-preview" aria-label="Uygulama iş akışı">
          <span>Vaka</span>
          <i aria-hidden="true" />
          <span>Onay</span>
          <i aria-hidden="true" />
          <span>Üretim</span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <DemoBanner />
          <div className="auth-card-heading">
            <p className="eyebrow">HESABINIZA ERİŞİN</p>
            <h2>Giriş yapın</h2>
            <p>Firebase hesabınızla güvenli oturum başlatın.</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <label htmlFor="email">E-posta</label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              placeholder="ornek@klinik.com"
              disabled={submitting}
              required
              autoFocus
            />

            <label htmlFor="password">Parola</label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="••••••••••••"
              disabled={submitting}
              required
            />

            <label className="remember-option">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(event) => setRememberMe(event.target.checked)}
                disabled={submitting}
              />
              <span>Oturumu açık tut</span>
            </label>

            {error !== null && (
              <div className="form-error" role="alert">
                {error}
              </div>
            )}

            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? "Giriş yapılıyor…" : "Giriş yap"}
            </button>
          </form>

          <p className="auth-footnote">Erişim sorunu yaşıyorsanız sistem yöneticisine başvurun.</p>
        </div>
      </section>
    </main>
  );
}
