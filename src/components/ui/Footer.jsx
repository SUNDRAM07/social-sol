import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="pt-4 text-sm text-[var(--muted)]">
      <div className="max-w-7xl mx-auto px-6 py-4 border-t border-[var(--border)] flex items-center justify-between">
        <div>© {new Date().getFullYear()} Agent Anywhere</div>
        <div className="flex items-center gap-4">
          <Link to="#">Terms</Link>
          <Link to="#">Privacy</Link>
        </div>
      </div>
    </footer>
  );
}

export default Footer;


