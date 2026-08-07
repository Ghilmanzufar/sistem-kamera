import React from 'react';

export default function ConfirmModal({ isOpen, title, message, confirmText = "Ya, Lanjutkan", cancelText = "Batal", onConfirm, onCancel, isDanger = false }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md p-6 glass-card shadow-2xl border border-white/10 rounded-2xl">
        <h3 className={`text-xl font-bold mb-2 ${isDanger ? 'text-rose-400' : 'text-white'}`}>
          {title}
        </h3>
        <p className="text-slate-300 text-sm mb-6 leading-relaxed">
          {message}
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-slate-300 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-semibold text-white rounded-lg transition-all ${isDanger
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
