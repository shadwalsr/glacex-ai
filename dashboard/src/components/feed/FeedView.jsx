import { useState } from 'react';
import { useApp } from '../../context/AppContext';
import SearchInput from '../common/SearchInput';
import CategoryPills from '../common/CategoryPills';
import FeedCard from './FeedCard';
import SpotlightPanel from './SpotlightPanel';

export default function FeedView() {
  const { 
    articles, 
    articlesLoading, 
    articlesError, 
    isOffline, 
    connectionError, 
    supabaseUrl, 
    drawerArticle, 
    openDrawer, 
    refetchArticles 
  } = useApp();

  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [showConfigModal, setShowConfigModal] = useState(false);

  const filteredArticles = articles.filter(a => {
    // Category filter
    if (activeCategory !== 'all') {
      const cls = Array.isArray(a.classifications) ? (a.classifications[0] || {}) : (a.classifications || {});
      const c = cls.category || 'other';
      if (c.toLowerCase() !== activeCategory) return false;
    }
    // Search filter
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      const titleMatch = a.title && a.title.toLowerCase().includes(q);
      const textMatch = a.clean_text && a.clean_text.toLowerCase().includes(q);
      if (!titleMatch && !textMatch) return false;
    }
    return true;
  });

  return (
    <div id="view-feed" className="max-w-container-max mx-auto w-full px-margin-mobile md:px-margin-desktop py-stack-lg">
      <div className="flex flex-col lg:flex-row gap-gutter">
        {/* Feed Column */}
        <section className="flex-grow w-full lg:w-2/3 flex flex-col">
          {/* Feed Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-stack-lg border-b border-border-subtle pb-stack-sm">
            <div>
              <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Intelligence Feed</h1>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1">High-signal technical developments.</p>
            </div>
            <div className="flex flex-wrap items-center gap-stack-sm">
              <SearchInput value={searchQuery} onChange={setSearchQuery} />
            </div>
          </div>

          {/* Offline / Data Lake Status Notice */}
          {isOffline && (
            <div className="mb-6 p-4 rounded-lg bg-[#0b0f19] border border-signal-medium/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-start sm:items-center gap-3">
                <div className="p-1.5 rounded bg-signal-medium/10 text-signal-medium shrink-0 mt-0.5 sm:mt-0">
                  <span className="material-symbols-outlined text-[18px]">cloud_off</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-signal-medium font-bold text-[11px] uppercase tracking-wider">Data Lake Offline</span>
                    <span className="text-[10px] text-on-surface-variant font-mono">({connectionError || 'Failed to fetch'})</span>
                  </div>
                  <p className="text-on-surface-variant text-[11px] mt-0.5">
                    Displaying cached offline intelligence corpus ({articles.length} signals). Live Supabase streaming is paused.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                <button
                  onClick={refetchArticles}
                  disabled={articlesLoading}
                  className="px-3 py-1.5 bg-surface-container hover:bg-surface-elevated text-primary border border-border-subtle rounded text-[11px] font-semibold transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <span className={`material-symbols-outlined text-[13px] ${articlesLoading ? 'animate-spin' : ''}`}>sync</span>
                  {articlesLoading ? 'Retrying...' : 'Retry Connection'}
                </button>
                <button
                  onClick={() => setShowConfigModal(true)}
                  className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded text-[11px] font-semibold transition cursor-pointer"
                >
                  Config Details
                </button>
              </div>
            </div>
          )}

          <CategoryPills activeCategory={activeCategory} onCategoryChange={setActiveCategory} />

          {/* Feed Card List */}
          <div id="feed-container" className="flex flex-col">
            {articlesLoading && articles.length === 0 && (
              <div className="text-center py-20 text-gray-500 font-mono">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary mb-4"></div>
                <p className="text-xs">Retrieving intelligence corpus...</p>
              </div>
            )}
            
            {articlesError && articles.length === 0 && (
              <div className="text-center py-20 bg-surface-elevated border border-signal-low/20 rounded p-8">
                <div className="text-signal-low font-mono text-xs mb-3">
                  // DATA_LAKE_CONNECTION_FAILED: {articlesError}
                </div>
                <p className="text-on-surface-variant text-xs mb-4">
                  Could not retrieve articles from Supabase or the fallback corpus.
                </p>
                <button
                  onClick={refetchArticles}
                  className="px-4 py-2 bg-primary text-surface-base font-semibold text-xs rounded hover:opacity-90 transition"
                >
                  Retry
                </button>
              </div>
            )}

            {!articlesLoading && filteredArticles.length === 0 && (
              <div className="text-center py-20 text-on-surface-variant font-mono text-xs">
                // Empty set. No matching signals found.
              </div>
            )}

            {filteredArticles.length > 0 && (
              filteredArticles.map((a, i) => (
                <FeedCard key={a.id} article={a} delay={i * 40} onClick={() => openDrawer(a.id)} />
              ))
            )}
          </div>
        </section>

        {/* Inline static preview area for desktop views */}
        <aside className="hidden lg:flex flex-col w-1/3 bg-surface-elevated border border-border-subtle p-stack-md rounded-lg inner-glow relative self-start">
          <div className="border-b border-border-subtle pb-stack-sm mb-stack-sm">
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-widest">Detail Spotlight</span>
          </div>
          <SpotlightPanel article={drawerArticle} />
        </aside>
      </div>

      {/* Supabase Connection Setup Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#090b14] border border-border-subtle rounded-xl max-w-lg w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-border-subtle mb-4">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-signal-medium">dns</span>
                <h3 className="font-headline-md text-primary font-bold text-base">Data Lake Configuration</h3>
              </div>
              <button 
                onClick={() => setShowConfigModal(false)}
                className="text-on-surface-variant hover:text-primary transition"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>

            <div className="space-y-4 text-xs text-on-surface-variant leading-relaxed">
              <div>
                <span className="font-bold text-primary block mb-1">Target Endpoint:</span>
                <code className="block bg-[#05060b] p-2.5 rounded border border-border-subtle font-mono text-signal-medium break-all">
                  {supabaseUrl || 'Not configured'}
                </code>
              </div>

              <div>
                <span className="font-bold text-primary block mb-1">Connection Diagnosis:</span>
                <p className="bg-[#05060b] p-2.5 rounded border border-border-subtle font-mono text-signal-low">
                  {connectionError || 'Failed to fetch (DNS non-existent domain / host paused)'}
                </p>
                <p className="mt-2 text-[11px]">
                  When a free-tier Supabase project is inactive, Supabase automatically pauses the instance and removes the DNS record.
                </p>
              </div>

              <div className="border-t border-border-subtle pt-3">
                <span className="font-bold text-primary block mb-1.5">To Connect a Live Database:</span>
                <ol className="list-decimal pl-4 space-y-1.5 text-[11px]">
                  <li>Log in to your <a href="https://supabase.com/dashboard" target="_blank" rel="noreferrer" className="text-primary underline">Supabase Dashboard</a> and restore or create a project.</li>
                  <li>Run migrations from repository root: <code className="bg-[#05060b] px-1 py-0.5 rounded text-primary">uv run python db/setup.py</code></li>
                  <li>Update <code className="bg-[#05060b] px-1 py-0.5 rounded text-primary">dashboard/.env</code> with your URL and anon key:</li>
                </ol>
                <pre className="bg-[#05060b] p-2.5 rounded border border-border-subtle font-mono text-[10px] text-primary mt-2">
{`VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>`}
                </pre>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-border-subtle pt-4">
              <button
                onClick={() => {
                  setShowConfigModal(false);
                  refetchArticles();
                }}
                className="px-4 py-2 bg-primary text-surface-base font-semibold text-xs rounded hover:opacity-90 transition cursor-pointer"
              >
                Retry Connection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
