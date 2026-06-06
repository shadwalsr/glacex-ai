function getArticleData(article) {
  const cls = Array.isArray(article.classifications) ? (article.classifications[0] || {}) : (article.classifications || {});
  const ins = Array.isArray(article.insights) ? (article.insights[0] || {}) : (article.insights || {});
  return { cls, ins };
}

export default function ResultCard({ article, index, onOpenDrawer }) {
  const { cls, ins } = getArticleData(article);
  const score = cls.importance || 0;
  
  let barColorClass = 'bg-signal-low';
  let signalColorClass = 'text-signal-low border-signal-low/20';
  if (score >= 75) {
    barColorClass = 'bg-signal-high';
    signalColorClass = 'text-signal-high border-signal-high/20';
  } else if (score >= 50) {
    barColorClass = 'bg-signal-medium';
    signalColorClass = 'text-signal-medium border-signal-medium/20';
  }

  return (
    <div 
      onClick={onOpenDrawer} 
      className="bg-surface-elevated border border-border-subtle rounded-lg p-stack-md hover:border-border-medium transition-colors group cursor-pointer inner-glow relative overflow-hidden fade-in hover-lift" 
      style={{ animationDelay: `${index * 45}ms` }}
    >
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${barColorClass} opacity-50 group-hover:opacity-100 transition-opacity`}></div>
      <div className="flex justify-between items-start mb-2 pl-2">
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded border text-[11px] font-mono ${signalColorClass}`}>{score}</span>
          <span className="font-label-sm text-label-sm text-on-surface-variant">ID: {article.id ? article.id.substring(0,8) : 'N/A'}</span>
        </div>
        <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors text-[18px]">bookmark_add</span>
      </div>
      <h4 className="font-body-lg text-body-lg font-bold text-primary mb-1 pl-2 truncate">{article.title}</h4>
      <p className="font-body-md text-body-md text-on-surface-variant pl-2 line-clamp-2">
        {ins.headline || cls.reason || "Structured summary pending."}
      </p>
    </div>
  );
}
