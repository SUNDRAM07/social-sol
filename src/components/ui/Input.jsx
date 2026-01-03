import { useId } from "react";
import clsx from "clsx";
import React from 'react';

export default function Input({ id, label, description, error, className = '', ...props }) {
  const inputId = id || `input_${Math.random().toString(36).slice(2, 9)}`;
  return (
    <div className={`flex flex-col space-y-1 ${className}`}>
      {label && <label htmlFor={inputId} className="text-sm font-medium">{label}</label>}
      <input
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={description || error ? `${inputId}-desc` : undefined}
        className={`px-3 py-2 border rounded-md text-sm bg-[var(--surface)] border-[var(--border)] focus-visible:shadow-[var(--ring)]`}
        {...props}
      />
      {description && !error && <div id={`${inputId}-desc`} className="text-xs text-[var(--text-muted)]">{description}</div>}
      {error && <div id={`${inputId}-desc`} className="text-xs text-[var(--danger)]">{error}</div>}
    </div>
  );
}

