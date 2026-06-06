function getArticleData(article) {
  const cls = Array.isArray(article.classifications) ? (article.classifications[0] || {}) : (article.classifications || {});
  const ins = Array.isArray(article.insights) ? (article.insights[0] || {}) : (article.insights || {});
  const fb = Array.isArray(article.user_feedback) ? (article.user_feedback[0] || {}) : (article.user_feedback || {});
  return { cls, ins, fb };
}

export default function FeedCard({ article, onClick, delay = 0 }) {
  const { cls, ins, fb } = getArticleData(article);
  const imp = cls.importance_score || 0;
  
  let impClass = 'text-signal-low border-signal-low/20';
  if (imp >= 75) {
    impClass = 'text-signal-high border-signal-high/20';
  } else if (imp >= 50) {
    impClass = 'text-signal-medium border-signal-medium/20';
  }

  let bookmarkIcon = 'bookmark_border';
  let bookmarkClass = 'text-on-surface-variant group-hover:text-primary';
  if (fb.rating === 'good') {
    bookmarkIcon = 'bookmark';
    bookmarkClass = 'text-primary';
  } else if (fb.rating === 'noise') {
    bookmarkIcon = 'bookmark_remove';
    bookmarkClass = 'text-signal-low';
  }

  return (
    <div 
      onClick={onClick}
      className="interactive-row border-b border-border-subtle py-stack-md px-2 flex flex-col md:flex-row gap-4 justify-between items-start cursor-pointer group fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex-grow">
        <div className="flex items-center gap-3 mb-2">
          <span className={`px-2 py-0.5 rounded border text-[11px] font-mono ${impClass}`}>{imp}</span>
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">{article.source_name || "Source"}</span>
          <span className="text-[10px] text-on-surface-variant/50">•</span>
          <span className="text-[10px] text-on-surface-variant font-mono">
            {article.scraped_at ? new Date(article.scraped_at).toLocaleDateString() : ""}
          </span>
        </div>
        <h3 className="font-headline-md text-headline-md text-primary font-bold group-hover:text-secondary transition-colors line-clamp-2">
          {article.title}
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2 line-clamp-2">
          {ins.headline || cls.reason || "Structured summary pending."}
        </p>
      </div>
      <div className="flex flex-row md:flex-col items-center justify-between h-full w-full md:w-auto shrink-0 mt-4 md:mt-0">
        <span 
          className={`material-symbols-outlined transition-colors ${bookmarkClass}`} 
          style={{ fontVariationSettings: fb.rating === 'good' ? "'FILL' 1" : "'FILL' 0" }}
        >
          {bookmarkIcon}
        </span>
        <div className="hidden md:flex shrink-0 w-8 h-8 rounded-full border border-border-subtle items-center justify-center group-hover:bg-primary group-hover:border-primary group-hover:text-surface-base transition-all duration-300 mt-8">
          <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
        </div>
      </div>
    </div>
  );
}
