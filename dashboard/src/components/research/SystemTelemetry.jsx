export default function SystemTelemetry({ nodeCount }) {
  return (
    <div className="bg-surface-elevated border border-border-subtle rounded p-stack-md inner-glow">
      <h2 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-stack-md text-[11px]">System Telemetry</h2>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex justify-between items-center border-b border-border-subtle pb-2">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Index Status</span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-signal-high shadow-[0_0_8px_#32D74B] animate-pulse"></div>
            <span className="font-label-md text-label-md text-primary">ONLINE</span>
          </div>
        </div>
        <div className="flex justify-between items-center border-b border-border-subtle pb-2">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Last Sync</span>
          <span className="font-stats-number text-stats-number text-primary">0.4s ago</span>
        </div>
        <div className="flex justify-between items-center border-b border-border-subtle pb-2">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Query Latency</span>
          <span className="font-stats-number text-stats-number text-primary">42ms</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Active Nodes</span>
          <span className="font-stats-number text-stats-number text-primary">{nodeCount !== undefined ? nodeCount : '--'}</span>
        </div>
      </div>
    </div>
  );
}
