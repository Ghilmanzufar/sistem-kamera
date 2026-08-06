import React from 'react';

export default function PageHeader({ title, highlightTitle, subtitle, actionButton }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 pb-6 border-b border-white/10 gap-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          {title} {highlightTitle && <span className="text-blue-500">{highlightTitle}</span>}
        </h1>
        {subtitle && <p className="text-slate-400 text-sm mt-1">{subtitle}</p>}
      </div>
      {actionButton && <div>{actionButton}</div>}
    </div>
  );
}
