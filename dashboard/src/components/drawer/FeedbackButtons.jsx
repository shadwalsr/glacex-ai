export default function FeedbackButtons({ rating, onFeedback }) {
  const isGood = rating === 'good';
  const isNoise = rating === 'noise';

  return (
    <div className="grid grid-cols-2 gap-3">
      <button 
        onClick={() => onFeedback('good')} 
        className={`w-full py-2.5 px-4 rounded font-label-md text-label-md font-bold transition flex justify-center items-center gap-2 ${
          isGood 
            ? 'bg-signal-high text-surface-base shadow-[0_0_15px_rgba(50,215,75,0.4)]' 
            : 'bg-primary text-surface-base hover:opacity-90'
        }`}
      >
        <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: isGood ? "'FILL' 1" : "'FILL' 0" }}>bookmark</span>
        <span>Keep Signal</span>
      </button>
      <button 
        onClick={() => onFeedback('noise')} 
        className={`w-full py-2.5 px-4 rounded border font-label-md text-label-md transition flex justify-center items-center gap-2 ${
          isNoise
            ? 'bg-signal-low/10 text-signal-low border-signal-low/50'
            : 'bg-transparent text-primary border-border-subtle hover:bg-surface-elevated'
        }`}
      >
        <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: isNoise ? "'FILL' 1" : "'FILL' 0" }}>bookmark_border</span>
        <span>Filter Noise</span>
      </button>
    </div>
  );
}
