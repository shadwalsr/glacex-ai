export default function EntityTags({ tags }) {
  if (!tags || tags.length === 0) {
    return <span className="text-xs text-on-surface-variant">No named entities mapped.</span>;
  }

  return (
    <>
      {tags.map((tag, i) => (
        <span key={i} className="px-2 py-1 rounded bg-[#0b0f19] border border-border-subtle text-[10px] text-on-surface-variant font-mono">
          {tag}
        </span>
      ))}
    </>
  );
}
