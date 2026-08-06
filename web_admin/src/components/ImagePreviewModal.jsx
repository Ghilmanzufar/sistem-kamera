import React from 'react';

export default function ImagePreviewModal({ isOpen, imageUrl, title = "Foto NG Record", onClose }) {
  if (!isOpen || !imageUrl) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn" onClick={onClose}>
      <div className="relative max-w-4xl max-h-[90vh] p-4 glass-card shadow-2xl border border-white/10 rounded-2xl flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
        <div className="w-full flex justify-between items-center mb-3 pb-2 border-b border-white/10">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl font-bold p-1">✕</button>
        </div>
        <div className="overflow-auto max-h-[75vh] flex justify-center">
          <img src={imageUrl} alt={title} className="rounded-lg object-contain max-w-full" />
        </div>
      </div>
    </div>
  );
}
