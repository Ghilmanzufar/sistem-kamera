import React from 'react';

export default function StatusBadge({ status }) {
  let badgeStyle = "bg-gray-500/20 text-gray-300 border-gray-500/30";
  let text = status;

  if (typeof status === 'number') {
    if (status === 1) {
      badgeStyle = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      text = "Selesai (OK)";
    } else if (status === 2) {
      badgeStyle = "bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse";
      text = "Running";
    } else {
      badgeStyle = "bg-rose-500/20 text-rose-400 border-rose-500/30";
      text = "NG / Gagal";
    }
  } else if (typeof status === 'string') {
    const s = status.toUpperCase();
    if (s.includes('OK') || s === 'SELESAI' || s === 'ACTIVE' || s === 'LOGIN') {
      badgeStyle = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    } else if (s.includes('RUNNING') || s === 'PENDING') {
      badgeStyle = "bg-amber-500/20 text-amber-400 border-amber-500/30";
    } else if (s.includes('NG') || s === 'FAILED' || s === 'LOGOUT' || s === 'DELETE') {
      badgeStyle = "bg-rose-500/20 text-rose-400 border-rose-500/30";
    } else {
      badgeStyle = "bg-blue-500/20 text-blue-400 border-blue-500/30";
    }
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${badgeStyle}`}>
      {text}
    </span>
  );
}
