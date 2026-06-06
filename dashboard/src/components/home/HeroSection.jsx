import { useNavigate } from 'react-router-dom';

export default function HeroSection({ children }) {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-[700px] flex flex-col items-center justify-center px-margin-mobile md:px-margin-desktop bg-grid-pattern hero-glow">
      <div className="hero-glow-orb"></div>
      <div className="max-w-4xl text-center space-y-stack-lg z-10 pt-12">
        <div className="hero-reveal hero-delay-1 inline-flex items-center gap-stack-sm px-stack-md py-unit bg-surface-elevated border border-border-subtle rounded-full mb-stack-md">
          <span className="w-2 h-2 rounded-full bg-signal-high"></span>
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">System Online v2.4</span>
        </div>
        <h1 className="hero-reveal hero-delay-2 hero-shimmer font-display-lg text-display-lg text-primary text-4xl md:text-6xl lg:text-7xl leading-tight">
          Autonomous Intelligence.<br/>
          <span className="hero-subtitle">Curated for the Technical Mind.</span>
        </h1>
        <p className="hero-reveal hero-delay-3 font-body-lg text-body-lg text-on-surface-variant max-w-2xl mx-auto pt-2">
          The engine that crawls, parses, and delivers high-signal AI developments directly to you. Built for architects who demand clarity without the noise.
        </p>
        <div className="hero-reveal hero-delay-4 flex flex-col sm:flex-row items-center justify-center gap-stack-md pt-stack-md">
          <button onClick={() => navigate('/feed')} className="w-full sm:w-auto font-body-md text-body-md bg-primary text-surface-base px-stack-lg py-stack-sm rounded hover:opacity-90 transition-opacity">Initialize Engine</button>
          <button onClick={() => navigate('/health')} className="w-full sm:w-auto font-body-md text-body-md bg-transparent border border-border-subtle text-primary px-stack-lg py-stack-sm rounded hover:bg-surface-elevated transition-colors">Read Documentation</button>
        </div>
      </div>
      {children}
    </section>
  );
}
