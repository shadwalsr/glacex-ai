import { useSources } from '../../hooks/useSources';
import SourceCard from './SourceCard';

export default function SourcesView() {
  const { sources, loading, error, refetch } = useSources(true);

  return (
    <div id="view-sources" className="max-w-container-max mx-auto w-full px-margin-mobile md:px-margin-desktop py-stack-lg">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Data Stream Sources</h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">Configured pipeline inputs spanning newsletter archives, RSS feeds, and technical journals.</p>
        </div>
        <button onClick={refetch} className="bg-surface-container hover:bg-surface-container-high text-primary border border-border-subtle text-xs font-semibold px-4 py-2 rounded transition flex-shrink-0">Sync Streams</button>
      </div>
      
      <div id="sources-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading && (
          <div className="col-span-full text-center py-20 text-on-surface-variant font-mono">Gathering registry components...</div>
        )}
        {error && (
          <div className="col-span-full text-center py-20 text-signal-low font-mono text-xs">Failed to load registry: {error}</div>
        )}
        {!loading && !error && sources.length === 0 && (
          <div className="col-span-full text-center py-20 text-on-surface-variant font-mono text-xs">// Registry empty. No streams active.</div>
        )}
        {!loading && !error && sources.map((s, i) => (
          <SourceCard key={s.id || i} source={s} index={i} />
        ))}
      </div>
    </div>
  );
}
