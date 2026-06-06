import { useTerminalSearch } from '../../hooks/useTerminalSearch';
import { useApp } from '../../context/AppContext';
import QueryInput from './QueryInput';
import ResultCard from './ResultCard';
import UMAPProjection from './UMAPProjection';
import SystemTelemetry from './SystemTelemetry';

export default function ResearchView() {
  const { results, loading, error, resultCount, search } = useTerminalSearch();
  const { articles, openDrawer } = useApp();

  return (
    <div id="view-terminal" className="max-w-container-max mx-auto w-full px-margin-mobile md:px-margin-desktop py-stack-lg">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-start">
        
        {/* Left Column: Search vector input & results */}
        <div className="lg:col-span-8 flex flex-col gap-stack-lg">
          <QueryInput onSearch={search} />

          {/* Research signals list output */}
          <div className="flex flex-col gap-stack-md">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2">
              <h3 className="font-headline-md text-headline-md font-medium text-primary">Research Signals</h3>
              <span className="font-label-sm text-label-sm text-on-surface-variant">
                {resultCount !== null ? `${resultCount} nodes matched` : 'Waiting for query execution...'}
              </span>
            </div>
            
            <div className="space-y-4">
              {loading && (
                <div className="text-center py-12 text-on-surface-variant font-mono text-xs">
                  <div className="inline-block animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-primary mb-2"></div>
                  <br/>// Executing vector similarity search...
                </div>
              )}
              {error && (
                <div className="bg-surface-container border border-error/20 text-error rounded p-6 text-center font-mono text-xs">
                  // SQL TERMINAL QUERY EXCEPTION: {error}
                </div>
              )}
              {!loading && !error && resultCount === 0 && (
                <div className="text-center py-12 text-on-surface-variant font-mono text-xs">
                  // Zero vectors matched query parameters.
                </div>
              )}
              {!loading && !error && resultCount === null && (
                <div className="text-center py-12 text-on-surface-variant font-mono text-xs">
                  // Ready to run search queries. Results will be rendered here.
                </div>
              )}
              {!loading && !error && results && results.length > 0 && (
                results.map((r, i) => (
                  <ResultCard key={r.id} article={r} index={i} onOpenDrawer={() => openDrawer(r.id)} />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: UMAP chart visualization & Telemetry stats */}
        <div className="lg:col-span-4 flex flex-col gap-stack-lg">
          <UMAPProjection />
          <SystemTelemetry nodeCount={articles.length} />
        </div>

      </div>
    </div>
  );
}
