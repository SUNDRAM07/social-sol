import React from 'react';

export default function Card({ children, className = '', title, footer }) {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="mb-3 flex items-center justify-between">
          {React.isValidElement(title) ? (
            title
          ) : (
            <div className="font-medium text-sm">{title}</div>
          )}
        </div>
      )}
      <div>{children}</div>
      {footer && <div className="mt-4 text-sm text-[var(--text-muted)]">{footer}</div>}
    </div>
  );
}
