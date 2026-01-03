import React from 'react';
import { useReactTable, getCoreRowModel } from '@tanstack/react-table';

export default function DataTable({ columns, data }) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <table className="w-full text-sm table-fixed">
        <thead className="bg-[var(--bg-muted)] text-[var(--text-muted)]">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id} className="px-4 py-3 text-left font-medium">{h.isPlaceholder ? null : h.column.columnDef.header}</th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-t hover:bg-[var(--bg-muted)]">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 align-middle">{cell.renderValue()}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
