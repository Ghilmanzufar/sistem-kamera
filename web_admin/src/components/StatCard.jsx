import React from 'react';

export default function StatCard({ title, value, icon: Icon, color = "blue" }) {
  const colorStyles = {
    blue: "from-blue-500/20 to-indigo-500/5 text-blue-400 border-blue-500/30",
    emerald: "from-emerald-500/20 to-teal-500/5 text-emerald-400 border-emerald-500/30",
    rose: "from-rose-500/20 to-red-500/5 text-rose-400 border-rose-500/30",
    amber: "from-amber-500/20 to-yellow-500/5 text-amber-400 border-amber-500/30",
  };

  return (
    <div className={`p-5 rounded-2xl border bg-gradient-to-br ${colorStyles[color] || colorStyles.blue} backdrop-blur-md shadow-lg`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-white">{value}</h3>
        </div>
        {Icon && (
          <div className="p-3 rounded-xl bg-white/5 border border-white/10">
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </div>
  );
}
