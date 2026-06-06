import { Link } from 'react-router-dom';

export default function AboutView() {
  const sitemap = [
    { path: '/', label: 'Home', desc: 'Latest previews and spotlight signals', icon: 'home' },
    { path: '/feed', label: 'Feed', desc: 'The main intelligence feed, ranked by importance', icon: 'list_alt' },
    { path: '/saved', label: 'Saved', desc: 'Your saved high-value signals', icon: 'bookmark' },
    { path: '/health', label: 'Architecture', desc: 'System architecture and pipeline health', icon: 'memory' },
    { path: '/terminal', label: 'Research', desc: 'Interactive research terminal', icon: 'terminal' },
    { path: '/sources', label: 'Sources', desc: 'Monitored data sources and feeds', icon: 'database' },
    { path: '/about', label: 'About', desc: 'About Glacex.ai and sitemap', icon: 'info' }
  ];

  return (
    <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg pb-32 fade-in">
      <div className="mb-stack-xl">
        <h1 className="font-display-lg text-display-lg text-3xl md:text-5xl font-bold tracking-tight text-primary mb-4">
          About Glacex.ai
        </h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl leading-relaxed">
          Glacex.ai is an autonomous intelligence platform engineered for technical minds. 
          In a landscape flooded with daily AI announcements, product launches, and academic papers, 
          finding genuinely impactful technical information is overwhelming. 
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-stack-xl">
        <div className="space-y-stack-md">
          <div className="bg-surface-elevated border border-border-subtle rounded-xl p-stack-md">
            <h2 className="text-xl font-bold text-secondary mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined">psychology</span>
              How It Works
            </h2>
            <div className="space-y-4 text-sm text-on-surface-variant leading-relaxed">
              <p>
                <strong className="text-primary">1. Data Ingestion:</strong> The Ingestion Agent continually scrapes unstructured data from high-signal configured sources (arXiv, elite engineering blogs, and newsletters). It hands this data to NLP Agents which use semantic embeddings to detect and drop redundant articles.
              </p>
              <p>
                <strong className="text-primary">2. Autonomous LLM Evaluation:</strong> Unique articles are passed to the LLM Agent, which leverages powerful models (Groq/Gemini) to perform deep semantic analysis. It evaluates technical depth, assigns an Importance Score (0-100), extracts entities, and writes a dense, structured insight.
              </p>
              <p>
                <strong className="text-primary">3. Real-time Dashboard:</strong> You are currently viewing the frontend dashboard. It surfaces these ranked articles, offering interactive deep-dives into the AI's classification reasoning, extracted concepts, and full article texts.
              </p>
            </div>
          </div>

          <div className="bg-surface-elevated border border-border-subtle rounded-xl p-stack-md">
            <h2 className="text-xl font-bold text-signal-high mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined">code</span>
              Tech Stack
            </h2>
            <ul className="space-y-3 text-sm text-on-surface-variant">
              <li className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-signal-high"></span>
                <span><strong className="text-primary">Backend:</strong> Python, Supabase (PostgreSQL)</span>
              </li>
              <li className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-signal-medium"></span>
                <span><strong className="text-primary">AI Models:</strong> Groq API, Google Gemini API</span>
              </li>
              <li className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-secondary"></span>
                <span><strong className="text-primary">Frontend:</strong> React, Vite, Tailwind CSS</span>
              </li>
              <li className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-tertiary-fixed"></span>
                <span><strong className="text-primary">CI/CD:</strong> GitHub Actions</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="space-y-stack-md">
          <div className="bg-[#05060b] border border-border-subtle rounded-xl p-stack-md h-full">
            <h2 className="text-xl font-bold text-primary mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined">map</span>
              Sitemap
            </h2>
            <div className="flex flex-col gap-3">
              {sitemap.map((item, index) => (
                <Link 
                  key={index} 
                  to={item.path}
                  className="flex items-start gap-4 p-3 rounded-lg hover:bg-surface-elevated border border-transparent hover:border-border-subtle transition-all duration-300 group"
                >
                  <div className="bg-surface-container w-10 h-10 rounded flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                    <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">
                      {item.icon}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-bold text-primary group-hover:text-secondary transition-colors text-sm">
                      {item.label}
                    </h3>
                    <p className="text-xs text-on-surface-variant mt-1">
                      {item.desc}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
