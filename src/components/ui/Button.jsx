import clsx from "clsx";

function Button({ variant = "primary", size = "md", className, children, ...props }) {
  const variants = {
    primary: "bg-[var(--primary)] text-[var(--primary-foreground)]",
    secondary: "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)]",
    gradient: "bg-gradient-to-r from-gradient-primary-start to-gradient-primary-end text-white",
    ghost: "bg-transparent text-[var(--text)] border border-[var(--border)]",
    destructive: "bg-[var(--danger)] text-white",
    success: "bg-green-600 text-white",
  };

  const sizes = {
    sm: "h-9 px-4 text-sm rounded-md",
    md: "h-11 px-5 text-base rounded-lg",
    lg: "h-12 px-6 text-lg rounded-lg",
  };

  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 font-semibold transition-all duration-300 focus-visible-ring active:scale-95 disabled:opacity-60 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
