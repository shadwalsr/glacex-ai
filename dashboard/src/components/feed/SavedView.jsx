import { useApp } from '../../context/AppContext';
import FeedCard from './FeedCard';

export default function SavedView() {
  const { articles, openDrawer, articlesLoading } = useApp();

  const savedArticles = articles.filter(article => {
    const fb = Array.isArray(article.user_feedback) ? article.user_feedback[0] : article.user_feedback;
    return fb?.rating === 'good';
  });

  if (articlesLoading) {
    return (
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg min-h-[50vh] flex items-center justify-center">
        <div className="flex items-center gap-3 text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin-slow">hourglass_empty</span>
          <span className="font-mono text-sm uppercase tracking-widest">Loading saved signals...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg pb-32">
      <div className="mb-stack-xl fade-in flex items-end justify-between">
        <div>
          <h1 className="font-display-lg text-display-lg text-3xl md:text-5xl font-bold tracking-tight text-primary mb-2">
            Saved Signals
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
            Articles you have marked as high-value signals.
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 bg-surface-elevated border border-border-subtle rounded px-4 py-2 text-sm text-on-surface-variant font-mono">
          <span className="text-signal-high font-bold">{savedArticles.length}</span> SIGNALS
        </div>
      </div>

      {savedArticles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-surface-elevated border border-border-subtle rounded-lg border-dashed fade-in">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant/50 mb-4">bookmark_border</span>
          <h3 className="text-lg font-bold text-primary mb-2">No saved signals</h3>
          <p className="text-on-surface-variant text-center max-w-md">
            When you find a high-value signal in your feed, open it and click "Good Signal" to save it here for future reference.
          </p>
        </div>
      ) : (
        <div className="flex flex-col border-t border-border-subtle">
          {savedArticles.map((article, index) => (
            <FeedCard 
              key={article.id} 
              article={article} 
              onClick={() => openDrawer(article.id)} 
              delay={index * 50} 
            />
          ))}
        </div>
      )}
    </div>
  );
}
