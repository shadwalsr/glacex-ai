export default function DrawerInsights({ insights }) {
  if (!insights || !insights.headline) return null;

  return (
    <div className="space-y-4 border-t border-border-subtle pt-4">
      <div className="border-l-2 border-primary pl-3">
        <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Key Discovery Headline</h4>
        <p className="text-sm font-bold text-primary mt-1">{insights.headline}</p>
      </div>
      {insights.tldr && insights.tldr.length > 0 && (
        <div>
          <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-2">Technical TL;DR</h4>
          <ul className="space-y-1.5 text-xs text-on-surface-variant leading-relaxed list-disc pl-4">
            {insights.tldr.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {insights.practical_utility && (
        <div>
          <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Practical Utility</h4>
          <p className="text-xs text-on-surface-variant leading-relaxed mt-1">{insights.practical_utility}</p>
        </div>
      )}
      {insights.ecosystem_impact && (
        <div>
          <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Ecosystem Impact</h4>
          <p className="text-xs text-on-surface-variant leading-relaxed mt-1">{insights.ecosystem_impact}</p>
        </div>
      )}
    </div>
  );
}
