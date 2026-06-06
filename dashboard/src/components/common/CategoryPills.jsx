export default function CategoryPills({ activeCategory, onCategoryChange }) {
  const categories = [
    { value: 'all', label: 'All Discoveries' },
    { value: 'paper', label: 'Papers' },
    { value: 'tool', label: 'Tools' },
    { value: 'product', label: 'Products' },
    { value: 'company', label: 'Companies' }
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 mb-stack-md">
      {categories.map((cat) => (
        <button
          key={cat.value}
          onClick={() => onCategoryChange(cat.value)}
          className={`cat-pill px-3 py-1 rounded text-xs font-semibold border transition ${
            activeCategory === cat.value
              ? "is-active bg-surface-container border-border-subtle text-on-surface-variant"
              : "bg-surface-container border-border-subtle text-on-surface-variant hover:text-primary"
          }`}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
}
