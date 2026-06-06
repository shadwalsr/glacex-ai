export default function ExecutionTable({ data, loading, error }) {
  return (
    <table className="w-full text-left text-xs text-on-surface">
      <thead className="bg-[#0b0f19]/70 text-on-surface-variant uppercase text-[10px] font-semibold border-b border-border-subtle">
        <tr>
          <th className="px-4 sm:px-6 py-4">Run Time</th>
          <th className="px-4 sm:px-6 py-4">Run ID</th>
          <th className="px-4 sm:px-6 py-4 text-center">Ingested</th>
          <th className="px-4 sm:px-6 py-4 text-center">Embedded</th>
          <th className="px-4 sm:px-6 py-4 text-center hidden sm:table-cell">Duplicates</th>
          <th className="px-4 sm:px-6 py-4 text-center">Signals</th>
          <th className="px-4 sm:px-6 py-4 text-center hidden sm:table-cell">Duration</th>
          <th className="px-4 sm:px-6 py-4 text-right">Health</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border-subtle bg-surface-base">
        {loading && (
          <tr><td colSpan="8" className="text-center py-12 text-on-surface-variant font-mono">Loading operations matrix...</td></tr>
        )}
        {error && (
          <tr><td colSpan="8" className="text-center py-12 text-signal-low font-mono">Operations matrix load failed: {error}</td></tr>
        )}
        {!loading && !error && (!data || data.length === 0) && (
          <tr><td colSpan="8" className="text-center py-12 text-on-surface-variant font-mono">No execution runs found.</td></tr>
        )}
        {!loading && !error && data && data.map((r, i) => {
          const run = r.pipeline_runs || {};
          const ds = new Date(r.created_at).toLocaleString(undefined, {dateStyle:"short",timeStyle:"short"});
          const rid = r.run_id ? r.run_id.substring(0,8) : "N/A";
          
          let textBadgeClass = "text-signal-high bg-signal-high/10 border-signal-high/20";
          if (r.health_score < 0.5) {
            textBadgeClass = "text-signal-low bg-signal-low/10 border-signal-low/20";
          } else if (r.health_score < 0.8) {
            textBadgeClass = "text-signal-medium bg-signal-medium/10 border-signal-medium/20";
          }

          return (
            <tr key={i} className="hover:bg-[#0b0f19]/30 transition">
              <td className="px-4 sm:px-6 py-4 font-semibold text-primary">{ds}</td>
              <td className="px-4 sm:px-6 py-4 font-mono text-xs text-on-surface-variant">{rid}...</td>
              <td className="px-4 sm:px-6 py-4 text-center text-on-surface-variant">{run.ingested || 0}</td>
              <td className="px-4 sm:px-6 py-4 text-center text-on-surface-variant">{run.embedded || 0}</td>
              <td className="px-4 sm:px-6 py-4 text-center text-on-surface-variant hidden sm:table-cell">{run.duplicates || 0}</td>
              <td className="px-4 sm:px-6 py-4 text-center text-primary font-bold">{r.new_signals || 0}</td>
              <td className="px-4 sm:px-6 py-4 text-center text-on-surface-variant hidden sm:table-cell">{run.duration_s || 0}s</td>
              <td className="px-4 sm:px-6 py-4 text-right">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${textBadgeClass}`}>
                  {Math.round(r.health_score*100)}%
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
