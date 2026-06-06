import { NavLink } from 'react-router-dom';

export default function Navbar() {
  const linkClass = ({ isActive }) =>
    isActive
      ? "nav-tab text-primary font-bold border-b-2 border-primary pb-1 cursor-pointer active:opacity-70 font-body-md text-body-md"
      : "nav-tab text-on-surface-variant font-medium hover:text-primary transition-colors duration-200 cursor-pointer active:opacity-70 font-body-md text-body-md";

  return (
    <nav className="fixed top-0 w-full z-30 bg-surface-base/90 backdrop-blur-md border-b border-border-subtle">
      <div className="max-w-container-max mx-auto flex items-center justify-between px-margin-mobile md:px-margin-desktop h-16">
        <div className="flex items-center gap-stack-md">
          <NavLink to="/" className="font-display-lg text-display-lg text-xl font-extrabold text-primary tracking-tighter hover:opacity-80 transition-opacity">
            GlaceX.ai
          </NavLink>
        </div>
        <div id="main-nav" className="hidden md:flex items-center gap-stack-lg">
          <NavLink to="/" className={linkClass} end>Home</NavLink>
          <NavLink to="/feed" className={linkClass}>Feed</NavLink>
          <NavLink to="/saved" className={linkClass}>Saved</NavLink>
          <NavLink to="/health" className={linkClass}>Architecture</NavLink>
          <NavLink to="/terminal" className={linkClass}>Research</NavLink>
          <NavLink to="/sources" className={linkClass}>Sources</NavLink>
        </div>
        <div className="flex items-center gap-stack-md">
          {/* Status pill */}
          <div className="flex items-center gap-2 bg-surface-container border border-border-subtle px-3 py-1.5 rounded-full text-xs">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-signal-high opacity-75 pulse-glow"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-signal-high"></span>
            </span>
            <span className="text-on-surface-variant font-label-sm text-[10px] uppercase tracking-wider">Active</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
