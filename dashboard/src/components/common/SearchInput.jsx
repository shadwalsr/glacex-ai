import { useState, useEffect } from 'react';

export default function SearchInput({ value, onChange, placeholder = "Filter feed contents..." }) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  useEffect(() => {
    const handler = setTimeout(() => {
      onChange(localValue);
    }, 150);
    return () => clearTimeout(handler);
  }, [localValue, onChange]);

  return (
    <div className="relative w-full md:w-64">
      <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]" style={{ fontVariationSettings: "'FILL' 0" }}>search</span>
      <input 
        type="text" 
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder} 
        className="w-full bg-[#050505] border border-border-subtle rounded py-1.5 pl-9 pr-3 text-primary text-xs focus:outline-none focus:border-border-medium focus:ring-0 placeholder-on-surface-variant/50"
      />
    </div>
  );
}
