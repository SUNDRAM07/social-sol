import { useEffect, useId, useState } from "react";
import clsx from "clsx";

function Textarea({ label, maxLength = 280, error, className, ...props }) {
  const id = useId();
  const [count, setCount] = useState(0);
  useEffect(() => {
    setCount(props.value?.length ?? 0);
  }, [props.value]);
  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-bold text-white/90 mb-3"
        >
          {label}
        </label>
      )}
      <textarea
        id={id}
        maxLength={maxLength}
        className={clsx(
          "w-full rounded-2xl glass-hover border backdrop-blur-sm text-sm text-white/90 placeholder-white/60",
          "px-4 py-3 min-h-[120px] resize-vertical transition-all duration-300",
          "focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-white/50",
          "hover:bg-white/10",
          error && "border-red-400/50 focus:border-red-400 focus:ring-red-400/50",
          className
        )}
        aria-invalid={!!error}
        onChange={(e) => setCount(e.target.value.length)}
        {...props}
      />
      <div className="mt-3 flex justify-between text-xs">
        {error ? <p className="text-red-300">{error}</p> : <span />}
        <p className="text-white/60 font-medium">
          {count}/{maxLength}
        </p>
      </div>
    </div>
  );
}

export default Textarea;
