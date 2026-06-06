import { useNavigate } from 'react-router-dom';

export default function HeroSection({ children }) {
  const navigate = useNavigate();

  return (
    <section className="relative min-h-[700px] flex flex-col items-center justify-center px-margin-mobile md:px-margin-desktop bg-grid-pattern hero-glow">
      <div className="hero-glow-orb"></div>
      <div className="max-w-4xl text-center space-y-stack-lg z-10 pt-12">

        <h1 className="hero-reveal hero-delay-2 font-display-lg text-display-lg text-primary text-4xl md:text-6xl lg:text-7xl leading-tight">
          <span className="hero-shimmer block">
            Autonomous Intelligence.<br/>
            <span className="hero-subtitle">Curated for the Technical Mind.</span>
          </span>
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
