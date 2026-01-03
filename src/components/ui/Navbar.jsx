import { Link } from "react-router-dom";
import Button from "./Button.jsx";
import ThemeToggle from "../ThemeToggle.jsx";

function Navbar() {
  const nav = [
    { to: "/dashboard", label: "Products" },
    { to: "/campaigns", label: "Solutions" },
    { to: "/analytics", label: "Resources" },
    { to: "/settings", label: "Pricing" },
  ];

  return (
    <header className="fixed left-[280px] right-0 top-0 z-30 backdrop-blur-sm bg-[color:var(--bg)/0.6] border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <nav aria-label="Primary" className="flex items-center gap-6">
          {nav.map((item) => (
            <Link key={item.to} to={item.to} className="text-sm font-medium text-[var(--fg)] hover:text-[var(--primary)] focus-visible-ring px-2 py-1 rounded">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link to="/pricing" className="text-sm text-[var(--muted)] hover:text-[var(--fg)]">Pricing</Link>
          <Button variant="primary" size="md">Book a Demo</Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export default Navbar;


