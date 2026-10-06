export function CaseCompletionBanner() {
  return (
    <section className="case-completion-banner" role="status">
      <span className="completion-check" aria-hidden="true">✓</span>
      <div>
        <strong>Vaka başarıyla tamamlandı</strong>
        <p>Ürün şubeye teslim edildi. Kayıt değiştirilemez; gerektiğinde teknisyen tarafından iade süreci başlatılabilir.</p>
      </div>
    </section>
  );
}
