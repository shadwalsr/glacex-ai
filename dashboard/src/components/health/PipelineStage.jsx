export default function PipelineStage({ number, title, description, status, tools }) {
  return (
    <section className="bg-surface-elevated border border-border-subtle rounded p-stack-md relative glow-edge group hover:border-border-medium transition-colors hover-glow">
      <div className="flex items-center justify-between mb-stack-md">
        <h2 className="font-headline-md text-headline-md text-primary flex items-center gap-stack-sm">
          <span className="font-label-md text-label-md text-on-surface-variant">{number}.</span> {title}
        </h2>
        {status === 'Active' && (
          <div className="flex items-center gap-unit px-stack-sm py-unit bg-surface-container rounded-full border border-border-subtle">
            <div className="w-2 h-2 rounded-full bg-signal-high"></div>
            <span className="font-label-sm text-label-sm text-signal-high uppercase text-[10px]">Active</span>
          </div>
        )}
      </div>
      <p className="font-body-md text-body-md text-on-surface-variant mb-stack-md">
        {description}
      </p>
      {tools && tools.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-sm mb-stack-md">
          {tools.map((t, i) => (
            <div key={i} className="bg-surface-container p-stack-sm border border-border-subtle rounded text-center">
              <span className="font-label-md text-label-md text-primary block mb-unit">{t.name}</span>
              <span className="font-label-sm text-label-sm text-on-surface-variant text-[11px]">{t.subtitle}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
