export default function UMAPProjection() {
  return (
    <div className="bg-surface-elevated border border-border-subtle rounded p-stack-md inner-glow flex flex-col h-[380px]">
      <div className="flex items-center justify-between mb-stack-sm shrink-0">
        <h2 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest text-[11px]">UMAP Projection</h2>
        <span className="material-symbols-outlined text-on-surface-variant text-[18px]">aspect_ratio</span>
      </div>
      <div className="flex-grow bg-[#050505] border border-border-subtle rounded relative overflow-hidden group umap-grid">
        <div className="absolute top-1/4 left-1/4 w-2.5 h-2.5 rounded-full bg-signal-high blur-[1px] group-hover:blur-none transition-all duration-300 shadow-[0_0_8px_#32D74B]"></div>
        <div className="absolute top-[28%] left-[22%] w-1.5 h-1.5 rounded-full bg-signal-high opacity-70"></div>
        <div className="absolute top-[22%] left-[26%] w-1.5 h-1.5 rounded-full bg-signal-high opacity-80"></div>
        <div className="absolute top-1/2 left-2/3 w-2.5 h-2.5 rounded-full bg-signal-medium blur-[1px] group-hover:blur-none transition-all duration-300 shadow-[0_0_8px_#FFD60A]"></div>
        <div className="absolute top-[48%] left-[63%] w-1.5 h-1.5 rounded-full bg-signal-medium opacity-60"></div>
        <div className="absolute bottom-1/4 left-1/2 w-2.5 h-2.5 rounded-full bg-signal-low blur-[1px] group-hover:blur-none transition-all duration-300 shadow-[0_0_8px_#FF453A]"></div>
        <div className="absolute bottom-2 right-2 text-[#444748] font-label-sm text-[10px]">n_neighbors: 15, min_dist: 0.1</div>
      </div>
    </div>
  );
}
