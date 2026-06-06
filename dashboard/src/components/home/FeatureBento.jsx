export default function FeatureBento() {
  const features = [
    {
      icon: "tune",
      title: "High Signal-to-Noise",
      desc: "Algorithms calibrated to ignore superficial updates, focusing exclusively on substantive architectural shifts and technical breakthroughs.",
      decorIcon: "filter_alt"
    },
    {
      icon: "merge",
      title: "Semantic Deduplication",
      desc: "Multiple sources reporting the same development are synthesized into a single, comprehensive briefing. No repetitive reading.",
      decorIcon: "layers_clear"
    },
    {
      icon: "notifications_active",
      title: "Fatigue-Free Delivery",
      desc: "Digest only what matters. Our pipeline ensures that your attention is reserved for signals above a configurable noise threshold.",
      decorIcon: "notifications"
    }
  ];

  return (
    <section className="py-stack-lg border-t border-border-subtle mt-24">
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop grid grid-cols-1 md:grid-cols-3 gap-gutter">
        {features.map((f, i) => (
          <div key={i} className="bg-surface-elevated border border-border-subtle p-stack-md rounded-lg group hover:border-border-medium transition-colors relative overflow-hidden hover-lift">
            <div className="w-10 h-10 bg-surface-container rounded-lg border border-border-subtle flex items-center justify-center mb-stack-md group-hover:scale-110 transition-transform duration-300">
              <span className="material-symbols-outlined text-primary">{f.icon}</span>
            </div>
            <h3 className="font-headline-md text-headline-md text-primary mb-stack-sm">{f.title}</h3>
            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
              {f.desc}
            </p>
            <span className="material-symbols-outlined absolute -right-4 -bottom-4 text-9xl text-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ fontVariationSettings: "'FILL' 1" }}>
              {f.decorIcon}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
