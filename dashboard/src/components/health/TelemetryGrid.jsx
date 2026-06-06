export default function TelemetryGrid({ healthData }) {
  const latest = healthData && healthData.length > 0 ? healthData[0] : null;

  let healthScoreLabel = '--';
  let healthScoreColor = 'text-white';
  if (latest) {
    const sc = latest.health_score;
    healthScoreLabel = Math.round(sc * 100) + '%';
    if (sc >= 0.8) healthScoreColor = 'text-signal-high';
    else if (sc >= 0.5) healthScoreColor = 'text-signal-medium';
    else healthScoreColor = 'text-signal-low';
  }

  const sourcesRate = latest ? `${latest.sources_successful}/${latest.sources_total}` : '--';
  const yieldCount = latest ? String(latest.new_signals) : '--';
  const llmRate = latest ? Math.round(latest.llm_success_rate * 100) + '%' : '--';

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-surface-elevated border border-border-subtle p-4 rounded inner-glow flex flex-col justify-between">
        <span className="text-on-surface-variant text-[10px] font-semibold uppercase tracking-wider">Latest Run Health</span>
        <span className={`text-xl font-extrabold mt-2 ${healthScoreColor}`}>{healthScoreLabel}</span>
        <span className="text-[9px] text-indigo-300 mt-1 block">Composite score</span>
      </div>
      <div className="bg-surface-elevated border border-border-subtle p-4 rounded inner-glow flex flex-col justify-between">
        <span className="text-on-surface-variant text-[10px] font-semibold uppercase tracking-wider">Source Scrapes</span>
        <span className="text-xl font-extrabold mt-2 text-white">{sourcesRate}</span>
        <span className="text-[9px] text-emerald-300 mt-1 block">Successful / Total</span>
      </div>
      <div className="bg-surface-elevated border border-border-subtle p-4 rounded inner-glow flex flex-col justify-between">
        <span className="text-on-surface-variant text-[10px] font-semibold uppercase tracking-wider">Signal Yield</span>
        <span className="text-xl font-extrabold mt-2 text-white">{yieldCount}</span>
        <span className="text-[9px] text-purple-300 mt-1 block">Target: 5 per run</span>
      </div>
      <div className="bg-surface-elevated border border-border-subtle p-4 rounded inner-glow flex flex-col justify-between">
        <span className="text-on-surface-variant text-[10px] font-semibold uppercase tracking-wider">LLM Parsing Rate</span>
        <span className="text-xl font-extrabold mt-2 text-white">{llmRate}</span>
        <span className="text-[9px] text-amber-300 mt-1 block">Pydantic validation rate</span>
      </div>
    </div>
  );
}
