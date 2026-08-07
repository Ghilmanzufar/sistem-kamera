import React from 'react';

export default function ImagePreviewModal({ isOpen, imageUrl, title = "Foto NG Record", onClose }) {
  if (!isOpen || !imageUrl) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn" onClick={onClose}>
      <div className="relative max-w-5xl max-h-[90vh] p-6 glass-card shadow-2xl border border-white/15 rounded-3xl flex flex-col items-center space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="w-full flex justify-between items-center pb-3 border-b border-white/10">
          <h3 className="text-2xl font-bold text-white tracking-wide">{title}</h3>
          <button onClick={onClose} className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white font-bold transition-all">✕</button>
        </div>
        <div className="overflow-auto max-h-[75vh] flex justify-center w-full">
          <img src={imageUrl} alt={title} className="rounded-2xl object-contain max-w-full shadow-lg" />
        </div>
      </div>
    </div>
  );
}
