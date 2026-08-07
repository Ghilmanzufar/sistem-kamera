import React from 'react';

export default function ConfirmModal({ isOpen, title, message, confirmText = "Ya, Lanjutkan", cancelText = "Batal", onConfirm, onCancel, isDanger = false }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-xl p-8 glass-card shadow-2xl border border-white/15 rounded-3xl space-y-4">
        <h3 className={`text-2xl font-bold mb-2 ${isDanger ? 'text-rose-400' : 'text-white'}`}>
          {title}
        </h3>
        <p className="text-slate-300 text-base mb-8 leading-relaxed">
          {message}
        </p>
        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onCancel}
            className="px-6 py-2.5 text-base font-semibold text-slate-300 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-6 py-2.5 text-base font-semibold text-white rounded-xl transition-all ${
              isDanger 
                ? 'bg-rose-600 hover:bg-rose-500 shadow-lg shadow-rose-600/30' 
                : 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-600/30'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
