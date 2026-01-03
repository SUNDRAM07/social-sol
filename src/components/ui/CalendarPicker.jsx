import React from 'react';
import Modal from './Modal.jsx';

export default function CalendarPicker({ open, onOpenChange, date, onChange }) {
  if (!open) return null;
  const start = new Date(date);
  start.setDate(start.getDate() - 3);
  const days = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date(start); d.setDate(start.getDate() + i); return d;
  });
  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Select date">
      <div className="grid grid-cols-7 gap-2">
        {days.map((d) => (
          <button key={d.toDateString()} onClick={() => { onChange(d); onOpenChange(false); }} className="p-2 rounded-md hover:bg-[var(--bg-muted)]">{d.toDateString().slice(0,10)}</button>
        ))}
      </div>
    </Modal>
  );
}
