import React from 'react';

export default function DataTable({ headers, children, isLoading, emptyMessage = "Tidak ada data ditemukan.", maxHeight, center = true }) {
  return (
    <div 
      className="w-full overflow-x-auto rounded-xl border border-white/10 bg-black/20 backdrop-blur-md shadow-xl"
      style={maxHeight ? { maxHeight, overflowY: 'auto' } : {}}
    >
      <table className="w-full border-collapse relative">
        <thead className={maxHeight ? "sticky top-0 z-10 shadow-md" : ""}>
          <tr className="border-b border-white/15 bg-white/5 text-xs font-bold uppercase tracking-wider text-slate-200">
            {headers.map((h, idx) => (
              <th key={idx} className={`p-4 ${center ? 'text-center' : 'text-left'}`}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5 text-sm text-slate-300">
          {isLoading ? (
            <tr>
              <td colSpan={headers.length} className="p-8 text-center text-slate-400 animate-pulse">
                Memuat data...
              </td>
            </tr>
          ) : React.Children.count(children) === 0 ? (
            <tr>
              <td colSpan={headers.length} className="p-8 text-center text-slate-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            children
          )}
        </tbody>
      </table>
    </div>
  );
}
