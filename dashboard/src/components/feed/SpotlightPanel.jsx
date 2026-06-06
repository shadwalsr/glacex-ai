function getArticleData(article) {
  const cls = Array.isArray(article.classifications) ? (article.classifications[0] || {}) : (article.classifications || {});
  const ins = Array.isArray(article.insights) ? (article.insights[0] || {}) : (article.insights || {});
  return { cls, ins };
}

export default function SpotlightPanel({ article }) {
  if (!article) {
    return (
      <div id="spotlight-fallback" className="py-12 text-center text-on-surface-variant text-xs font-mono">
        Select an active feed item to inspect technical dimensions and submit feedback actions.
      </div>
    );
  }

  const { cls, ins } = getArticleData(article);
  const imp = cls.importance_score || 0;
  
  let impClass = 'text-signal-low';
  if (imp >= 75) {
    impClass = 'text-signal-high';
  } else if (imp >= 50) {
    impClass = 'text-signal-medium';
  }

  return (
    <div className="fade-in">
      <div className="flex justify-between items-start mb-4">
        <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border bg-surface-container border-border-subtle text-on-surface-variant">
          {cls.category || 'OTHER'}
        </span>
        <span className={`text-xl font-extrabold ${impClass}`}>{imp}</span>
      </div>
      <h3 className="text-sm font-bold text-primary mb-2 line-clamp-2">{article.title}</h3>
      <div className="bg-[#050505] border border-border-subtle p-3 rounded mt-4">
        <p className="text-[11px] text-on-surface-variant leading-relaxed line-clamp-6">
          {cls.reason || ins.headline || "Pending assessment."}
        </p>
      </div>
    </div>
  );
}
