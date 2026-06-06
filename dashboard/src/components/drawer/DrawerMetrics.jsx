import { useEffect, useState } from 'react';

export default function DrawerMetrics({ importance, depth }) {
  const [barWidth, setBarWidth] = useState(0);

  useEffect(() => {
    // Add a slight delay for the bar animation to run after mount
    const timer = setTimeout(() => {
      setBarWidth(importance);
    }, 100);
    return () => clearTimeout(timer);
  }, [importance]);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      <div className="bg-surface-container border border-border-subtle p-3 rounded flex flex-col gap-1">
        <span className="text-on-surface-variant text-[10px] uppercase font-bold tracking-wider">Confidence</span>
        <div className="flex items-baseline gap-1 mt-1">
          <span className="text-2xl font-extrabold text-primary">{importance}</span>
          <span className="text-on-surface-variant text-[9px]">/100</span>
        </div>
        <div className="w-full bg-surface-elevated rounded-full h-1 mt-1.5 overflow-hidden">
          <div 
            className="bg-primary h-1 rounded-full transition-all duration-500" 
            style={{ width: `${barWidth}%` }}
          ></div>
        </div>
      </div>
      <div className="bg-surface-container border border-border-subtle p-3 rounded flex flex-col justify-between">
        <span className="text-on-surface-variant text-[10px] uppercase font-bold tracking-wider">Depth</span>
        <div className="text-sm font-bold text-primary mt-1 flex items-center gap-1.5 truncate">
          <span className="h-2 w-2 rounded-full bg-signal-medium flex-shrink-0"></span>
          <span className="truncate">{depth}</span>
        </div>
      </div>
      <div className="bg-surface-container border border-border-subtle p-3 rounded flex flex-col justify-between col-span-2 sm:col-span-1">
        <span className="text-on-surface-variant text-[10px] uppercase font-bold tracking-wider">AI Relevancy</span>
        <div className="text-sm font-bold text-signal-high mt-1 flex items-center gap-1">
          <span className="material-symbols-outlined text-[16px]">verified</span>
          <span>Verified</span>
        </div>
      </div>
    </div>
  );
}
