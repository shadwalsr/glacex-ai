export default function StatusPill({ status, label }) {
  const isActive = status === 'active';
  
  return (
    <div className="flex items-center gap-2 bg-surface-container border border-border-subtle px-3 py-1.5 rounded-full text-xs">
      <span className="relative flex h-2 w-2">
        {isActive && <span className="absolute inline-flex h-full w-full rounded-full bg-signal-high opacity-75 pulse-glow"></span>}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${isActive ? 'bg-signal-high' : 'bg-on-surface-variant'}`}></span>
      </span>
      <span className="text-on-surface-variant font-label-sm text-[10px] uppercase tracking-wider">{label}</span>
    </div>
  );
}
