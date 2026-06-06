export default function Footer() {
  return (
    <footer className="bg-surface-base border-t border-border-subtle w-full py-stack-lg mt-12 bg-[#05060b]">
      <div className="flex flex-col md:flex-row justify-between items-center px-margin-desktop w-full max-w-container-max mx-auto gap-gutter text-xs text-on-surface-variant">
        <div className="font-label-md text-label-md font-bold text-primary">GlaceX.ai</div>
        <div>© 2026 GlaceX.ai. Technical Precision for Autonomous Systems.</div>
        <div className="flex flex-wrap justify-center gap-stack-md">
          <span className="hidden sm:inline">Connected Node: SUPABASE_US_EAST</span>
          <a href="https://github.com/shadwalsr/glacex-ai" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors duration-200">GitHub Repo</a>
        </div>
      </div>
    </footer>
  );
}
