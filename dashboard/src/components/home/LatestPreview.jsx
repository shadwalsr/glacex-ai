import { useApp } from '../../context/AppContext';

function getArticleData(article) {
  const cls = Array.isArray(article.classifications) ? (article.classifications[0] || {}) : (article.classifications || {});
  const ins = Array.isArray(article.insights) ? (article.insights[0] || {}) : (article.insights || {});
  return { cls, ins };
}

export default function LatestPreview() {
  const { articles, openDrawer } = useApp();
  const topArticles = articles.slice(0, 2);

  if (topArticles.length === 0) {
    return (
      <div className="hero-reveal hero-delay-5 hero-float mt-20 w-full max-w-3xl relative z-10 px-4">
        <div className="absolute inset-0 bg-primary/5 blur-3xl rounded-full"></div>
        <div className="relative bg-surface-elevated/80 backdrop-blur-md border border-border-medium rounded-xl p-stack-lg shadow-[0_0_40px_rgba(0,0,0,0.5)] overflow-hidden text-center text-on-surface-variant font-mono">
          No active signals available.
        </div>
      </div>
    );
  }

  return (
    <div className="hero-reveal hero-delay-5 hero-float mt-20 w-full max-w-3xl relative z-10 px-4 hover-lift">
      <div className="absolute inset-0 bg-primary/5 blur-3xl rounded-full"></div>
      <div className="relative bg-surface-elevated/80 backdrop-blur-md border border-border-medium rounded-xl p-stack-lg shadow-[0_0_40px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
        {/* Header */}
        <div className="flex justify-between items-center border-b border-border-subtle pb-stack-sm mb-stack-md">
          <h3 className="font-label-md text-label-md text-on-surface uppercase tracking-wider">Latest Intelligence</h3>
          <div className="flex gap-unit">
            <div className="w-2 h-2 rounded-full bg-surface-variant"></div>
            <div className="w-2 h-2 rounded-full bg-surface-variant"></div>
            <div className="w-2 h-2 rounded-full bg-surface-variant"></div>
          </div>
        </div>
        
        {/* Article Items */}
        <div className="space-y-4">
          {topArticles.map((a, i) => {
            const { cls, ins } = getArticleData(a);
            const imp = cls.importance_score || 0;
            let impLabel = 'Low Impact';
            let impClass = 'bg-signal-low/10 border-signal-low/20 text-signal-low';
            if (imp >= 75) {
              impLabel = 'High Impact';
              impClass = 'bg-signal-high/10 border-signal-high/20 text-signal-high';
            } else if (imp >= 50) {
              impLabel = 'Medium Impact';
              impClass = 'bg-signal-medium/10 border-signal-medium/20 text-signal-medium';
            }

            return (
              <div 
                key={a.id} 
                onClick={() => openDrawer(a.id)}
                className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between p-3 rounded hover:bg-surface-base transition-colors cursor-pointer border border-transparent hover:border-border-subtle group"
              >
                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${impClass}`}>
                      {impLabel}
                    </span>
                    <span className="text-on-surface-variant text-[10px] uppercase tracking-widest font-semibold">{a.source_name || "Source"}</span>
                  </div>
                  <h4 className="font-body-lg text-body-lg font-bold text-primary group-hover:text-secondary transition-colors line-clamp-1">{a.title}</h4>
                  <p className="text-on-surface-variant text-sm line-clamp-1 mt-1">{ins.headline || cls.reason || "Structured summary pending."}</p>
                </div>
                <div className="hidden sm:flex shrink-0 w-8 h-8 rounded-full bg-surface-base border border-border-subtle items-center justify-center group-hover:bg-primary group-hover:border-primary group-hover:text-surface-base transition-all duration-300">
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
