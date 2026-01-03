import clsx from "clsx";

function Badge({ color = "gray", className, children }) {
  const map = {
    gray: "bg-[var(--card)] text-[var(--fg)] border-[var(--border)]",
    green: "bg-green-600/10 text-green-400 border-green-600/20",
    yellow: "bg-yellow-500/10 text-yellow-300 border-yellow-500/20",
    red: "bg-[var(--destructive)]/10 text-[var(--destructive)] border-[var(--destructive)]/20",
    blue: "bg-blue-600/10 text-blue-300 border-blue-600/20",
    primary: "bg-gradient-primary/20 text-white border-[var(--border)]",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-sm border transition-all duration-300 hover:scale-105",
        map[color] || map.gray,
        className
      )}
    >
      {children}
    </span>
  );
}

export default Badge;
