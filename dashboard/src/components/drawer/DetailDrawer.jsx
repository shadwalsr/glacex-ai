import { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { submitFeedback as apiSubmitFeedback } from '../../api/supabase';
import EntityTags from '../common/EntityTags';
import DrawerMetrics from './DrawerMetrics';
import DrawerInsights from './DrawerInsights';
import FeedbackButtons from './FeedbackButtons';

export default function DetailDrawer() {
  const { drawerArticle, closeDrawer, updateArticleFeedback } = useApp();
  const [isClosing, setIsClosing] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (drawerArticle) {
      setIsVisible(true);
      setIsClosing(false);
    } else {
      setIsVisible(false);
    }
  }, [drawerArticle]);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') handleClose();
    };
    if (isVisible) {
      window.addEventListener('keydown', handleEscape);
    }
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isVisible]);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      closeDrawer();
    }, 300); // Wait for transition
  };

  const handleFeedback = async (rating) => {
    if (!drawerArticle) return;
    try {
      await apiSubmitFeedback(drawerArticle.id, rating);
      updateArticleFeedback(drawerArticle.id, rating);
    } catch (err) {
      console.error("Failed to submit feedback", err);
    }
  };

  if (!drawerArticle && !isClosing) return null;

  const article = drawerArticle || {};
  const cls = Array.isArray(article.classifications) ? (article.classifications[0] || {}) : (article.classifications || {});
  const ins = Array.isArray(article.insights) ? (article.insights[0] || {}) : (article.insights || {});
  const fb = Array.isArray(article.user_feedback) ? (article.user_feedback[0] || {}) : (article.user_feedback || {});

  const catColors = {
    'paper': 'bg-signal-high/10 text-signal-high border-signal-high/20',
    'tool': 'bg-secondary/10 text-secondary border-secondary/20',
    'product': 'bg-tertiary-container/10 text-tertiary-fixed border-tertiary-container/20',
    'company': 'bg-signal-medium/10 text-signal-medium border-signal-medium/20'
  };
  const catColor = catColors[cls.category] || 'bg-surface-container text-on-surface-variant border-border-subtle';

  let host = 'Source';
  try { if (article.url) host = new URL(article.url).hostname; } catch(e){}

  const showDrawer = isVisible && !isClosing;

  return (
    <>
      <div 
        onClick={handleClose} 
        className={`drawer-backdrop fixed inset-0 bg-black/70 backdrop-blur-sm z-40 ${showDrawer ? 'is-visible' : ''}`}
      ></div>

      <div className={`detail-drawer fixed top-0 right-0 h-full w-full max-w-lg md:max-w-2xl bg-[#090b14] border-l border-border-subtle shadow-2xl z-50 flex flex-col overflow-hidden ${showDrawer ? 'is-open' : ''}`}>
        {/* Header */}
        <div className="px-4 sm:px-6 py-4 border-b border-border-subtle flex items-center justify-between flex-shrink-0 bg-[#090b14]/50 backdrop-blur-md">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border flex-shrink-0 ${catColor}`}>
              {cls.category || 'OTHER'}
            </span>
            <span className="text-xs text-on-surface-variant font-semibold truncate font-mono">{host}</span>
          </div>
          <button onClick={handleClose} className="close-btn" aria-label="Close drawer" title="Close">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-grow overflow-y-auto px-4 sm:px-6 py-6 space-y-6 select-text bg-[#090b14]">
          <div>
            <h2 className="font-headline-md text-headline-md text-lg sm:text-xl md:text-2xl font-bold tracking-tight text-primary leading-tight">
              {article.title}
            </h2>
            <p className="text-[10px] text-on-surface-variant mt-2 font-mono">
              {article.scraped_at ? new Date(article.scraped_at).toLocaleString() : ""}
            </p>
          </div>

          <DrawerMetrics importance={cls.importance || 0} depth={cls.technical_depth || 'Standard'} />

          <div className="bg-surface-elevated border border-border-subtle rounded p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-primary mb-1.5">Classification Assessment</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed">{cls.reason || 'Pending assessment.'}</p>
          </div>

          <DrawerInsights insights={ins} />

          {article.clean_text && (
            <div className="border-t border-border-subtle pt-4 mt-6">
              <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-2">Extracted Content</h4>
              <div className="bg-[#05060b] border border-border-subtle rounded p-4 max-h-80 overflow-y-auto">
                <p className="text-sm text-on-surface-variant leading-relaxed whitespace-pre-wrap">
                  {article.clean_text}
                </p>
              </div>
            </div>
          )}

          <div className="border-t border-border-subtle pt-4 mt-6">
            <h4 className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-2">Extracted Entities & Concepts</h4>
            <div className="flex flex-wrap gap-1.5">
              <EntityTags tags={cls.entities || []} />
            </div>
          </div>
        </div>

        {/* Footer buttons */}
        <div className="px-4 sm:px-6 py-4 border-t border-border-subtle bg-surface-base flex flex-col gap-3 flex-shrink-0">
          <div className="flex items-center justify-between w-full">
            <a href={article.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs text-primary hover:underline font-semibold transition">
              <span>View Source Document</span>
              <span className="material-symbols-outlined text-[14px]">open_in_new</span>
            </a>
          </div>
          <FeedbackButtons rating={fb.rating} onFeedback={handleFeedback} />
        </div>
      </div>
    </>
  );
}
