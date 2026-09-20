import React from 'react';
import { X, Trash2, Clock, ArrowRight } from 'lucide-react';
import type { SegmentationResult } from '../types';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  history: SegmentationResult[];
  onSelectResult: (result: SegmentationResult) => void;
  onClearHistory: () => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  history,
  onSelectResult,
  onClearHistory,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-[#0d1322] border-l border-slate-800 h-full flex flex-col shadow-2xl p-5">
        {/* Drawer Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h3 className="font-bold text-white text-base">История обработок</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
              {history.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer List */}
        <div className="flex-1 overflow-y-auto py-4 space-y-3">
          {history.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              История пока пуста. Запустите сегментацию, чтобы сохранить результат.
            </div>
          ) : (
            history.map((item, idx) => (
              <div
                key={item.id || idx}
                onClick={() => {
                  onSelectResult(item);
                  onClose();
                }}
                className="group p-3 rounded-xl bg-slate-900/70 hover:bg-slate-800/80 border border-slate-800 hover:border-cyan-500/40 transition-all cursor-pointer flex items-center gap-3"
              >
                {/* Thumbnail */}
                <div className="w-16 h-16 rounded-lg overflow-hidden bg-black flex-shrink-0 border border-slate-800">
                  <img
                    src={item.images.overlay}
                    alt="Result thumbnail"
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span
                      className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                        item.task === 'road'
                          ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {item.task === 'road' ? 'Дороги' : 'Здания'}
                    </span>
                    {item.tta && (
                      <span className="text-[9px] px-1 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800">
                        TTA
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-medium text-slate-200 truncate">
                    {item.filename || 'aerial_photo.png'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {item.dimensions.width}×{item.dimensions.height} • {item.telemetry.inference_time_ms} мс
                  </p>
                </div>

                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
              </div>
            ))
          )}
        </div>

        {/* Drawer Footer */}
        {history.length > 0 && (
          <div className="pt-3 border-t border-slate-800">
            <button
              onClick={onClearHistory}
              className="w-full py-2.5 rounded-xl border border-red-900/50 bg-red-950/20 hover:bg-red-950/40 text-red-400 text-xs font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Очистить историю сессии</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
