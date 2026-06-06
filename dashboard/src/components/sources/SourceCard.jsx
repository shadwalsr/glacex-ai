export default function SourceCard({ source, index }) {
  const st = source.type || "httpx";
  
  let typeColorClass = "text-secondary bg-secondary/5 border-secondary/10";
  if (st === "playwright") {
    typeColorClass = "text-tertiary-container bg-tertiary-container/5 border-tertiary-container/10";
  } else if (st === "rss") {
    typeColorClass = "text-signal-high bg-signal-high/5 border-signal-high/10";
  }

  let host = "Unknown Stream";
  try {
    if (source.url) host = new URL(source.url).hostname;
  } catch(e) {}
  
  const cat = source.category || "General";

  return (
    <div 
      className="bg-surface-elevated border border-border-subtle rounded-lg p-5 hover:border-border-medium transition-colors group inner-glow flex flex-col justify-between fade-in hover-lift" 
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className={`px-2 py-0.5 rounded text-[9px] font-bold border uppercase ${typeColorClass}`}>{st}</span>
          {source.active ? (
            <span className="bg-signal-high/10 text-signal-high border border-signal-high/20 text-[9px] px-2 py-0.5 rounded font-bold uppercase">Active</span>
          ) : (
            <span className="bg-surface-container text-on-surface-variant border border-border-subtle text-[9px] px-2 py-0.5 rounded font-bold uppercase">Muted</span>
          )}
        </div>
        <h3 className="text-sm font-bold text-primary mb-1 line-clamp-1 group-hover:text-secondary transition-colors">{source.name}</h3>
        <a href={source.url} target="_blank" rel="noreferrer" className="text-[10px] text-on-surface-variant font-mono hover:text-primary transition-colors block mb-4 truncate">{host}</a>
      </div>
      <div className="pt-4 border-t border-border-subtle flex items-center justify-between text-[9px] font-mono text-on-surface-variant flex-wrap gap-1">
        <span>CAT: {cat.toUpperCase()}</span>
        <span>Sync: {source.last_scraped ? new Date(source.last_scraped).toLocaleDateString() : "Never"}</span>
      </div>
    </div>
  );
}
