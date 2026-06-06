import { useState } from 'react';
import { useApp } from '../../context/AppContext';
import SearchInput from '../common/SearchInput';
import CategoryPills from '../common/CategoryPills';
import FeedCard from './FeedCard';
import SpotlightPanel from './SpotlightPanel';

export default function FeedView() {
  const { articles, articlesLoading, articlesError, drawerArticle, openDrawer } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');

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

          <CategoryPills activeCategory={activeCategory} onCategoryChange={setActiveCategory} />

          {/* Feed Card List */}
          <div id="feed-container" className="flex flex-col">
            {articlesLoading && (
              <div className="text-center py-20 text-gray-500 font-mono">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary mb-4"></div>
                <p className="text-xs">Retrieving intelligence corpus...</p>
              </div>
            )}
            
            {articlesError && (
              <div className="text-center py-20 text-signal-low font-mono text-xs">
                // DATA_LAKE_CONNECTION_FAILED: {articlesError}
              </div>
            )}

            {!articlesLoading && !articlesError && filteredArticles.length === 0 && (
              <div className="text-center py-20 text-on-surface-variant font-mono text-xs">
                // Empty set. No matching signals found.
              </div>
            )}

            {!articlesLoading && !articlesError && filteredArticles.length > 0 && (
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
    </div>
  );
}
