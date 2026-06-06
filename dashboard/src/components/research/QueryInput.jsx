import { useState } from 'react';

export default function QueryInput({ onSearch }) {
  const [query, setQuery] = useState('');

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onSearch(query);
    }
  };

  return (
    <div className="bg-surface-elevated border border-border-subtle rounded p-stack-md inner-glow">
      <div className="flex items-center justify-between mb-stack-sm">
        <h2 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">Query Terminal</h2>
        <div className="flex items-center gap-2 bg-surface-container-high rounded p-1">
          <button className="px-3 py-1 rounded bg-surface-overlay border border-border-medium text-primary font-label-sm text-label-sm transition-colors text-[10px]">SEMANTIC</button>
          <button className="px-3 py-1 rounded text-on-surface-variant hover:text-primary font-label-sm text-label-sm transition-colors text-[10px]">REGEX</button>
        </div>
      </div>
      <div className="relative">
        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant" style={{ fontVariationSettings: "'FILL' 0" }}>search</span>
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter multi-dimensional semantic query..." 
          className="w-full bg-[#050505] border border-border-subtle rounded py-4 pl-12 pr-24 text-primary font-body-md focus:outline-none focus:border-border-medium focus:ring-0 shadow-inner placeholder-on-surface-variant/40"
        />
        <button 
          onClick={() => onSearch(query)} 
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-surface-overlay border border-border-subtle hover:border-border-medium text-primary px-3 py-1.5 rounded font-label-sm text-label-sm transition-colors"
        >
          EXECUTE
        </button>
      </div>
      <div className="mt-3 flex gap-4 text-on-surface-variant font-label-sm text-label-sm text-[11px]">
        <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">tune</span> Dimensions: 1536</span>
        <span className="flex items-center gap-1"><span className="material-symbols-outlined text-[14px]">layers</span> Corpus: Supabase-Articles</span>
      </div>
    </div>
  );
}
