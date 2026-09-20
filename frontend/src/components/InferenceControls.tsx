import React from 'react';
import { HelpCircle, Play, Loader2, Compass, Building2 } from 'lucide-react';
import type { TaskType } from '../types';

interface InferenceControlsProps {
  task: TaskType;
  setTask: (task: TaskType) => void;
  tta: boolean;
  setTta: (tta: boolean) => void;
  opacity: number;
  setOpacity: (opacity: number) => void;
  onRun: () => void;
  isLoading: boolean;
  elapsedSeconds: number;
  disabled: boolean;
}

export const InferenceControls: React.FC<InferenceControlsProps> = ({
  task,
  setTask,
  tta,
  setTta,
  opacity,
  setOpacity,
  onRun,
  isLoading,
  elapsedSeconds,
  disabled,
}) => {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-5">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Параметры инференса
      </div>

      {/* Task Selector: 2 large cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Road Task */}
        <button
          type="button"
          disabled={isLoading}
          onClick={() => setTask('road')}
          className={`relative p-3.5 rounded-xl border text-left transition-all ${
            task === 'road'
              ? 'border-cyan-400 bg-cyan-950/20 ring-1 ring-cyan-400/50 shadow-md shadow-cyan-950/50'
              : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-800/30'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <Compass className={`w-4 h-4 ${task === 'road' ? 'text-cyan-400' : 'text-slate-400'}`} />
            <span className="font-semibold text-sm text-white">Дороги</span>
            <span className="text-[10px] px-1 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 ml-auto">
              Основная
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Трассировка магистралей, улиц и развязок (Combo Loss)
          </p>
        </button>

        {/* Building Task */}
        <button
          type="button"
          disabled={isLoading}
          onClick={() => setTask('building')}
          className={`relative p-3.5 rounded-xl border text-left transition-all ${
            task === 'building'
              ? 'border-emerald-400 bg-emerald-950/20 ring-1 ring-emerald-400/50 shadow-md shadow-emerald-950/50'
              : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-800/30'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <Building2 className={`w-4 h-4 ${task === 'building' ? 'text-emerald-400' : 'text-slate-400'}`} />
            <span className="font-semibold text-sm text-white">Здания</span>
          </div>
          <p className="text-xs text-slate-400">
            Контуры крыш, жилых массивов и промышленных объектов
          </p>
        </button>
      </div>

      {/* TTA Toggle & Opacity Slider */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
        {/* TTA Switch */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1 text-xs font-medium text-slate-200">
              <span>Режим TTA (Аугментация)</span>
              <div className="relative group cursor-pointer">
                <HelpCircle className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400" />
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-slate-800 border border-slate-700 text-[11px] text-slate-300 rounded shadow-xl z-50 pointer-events-none">
                  Test-Time Augmentation: усреднение предсказаний для оригинала и отражений. Повышает точность (+1% IoU), но требует больше времени.
                </div>
              </div>
            </div>
            <p className="text-[11px] text-slate-500">Точнее, но медленнее</p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={tta}
              onChange={(e) => setTta(e.target.checked)}
              disabled={isLoading}
              className="sr-only peer"
            />
            <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
          </label>
        </div>

        {/* Opacity slider */}
        <div className="flex flex-col justify-center p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-300">
            <span>Прозрачность маски</span>
            <span className="font-mono text-cyan-400">{Math.round(opacity * 100)}%</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="0.9"
            step="0.05"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg cursor-pointer accent-cyan-400"
          />
        </div>
      </div>

      {/* Launch Action Button */}
      <button
        type="button"
        onClick={onRun}
        disabled={disabled || isLoading}
        className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm tracking-wide transition-all shadow-lg flex items-center justify-center gap-2 ${
          disabled || isLoading
            ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
            : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-cyan-500/25 hover:shadow-cyan-500/40 active:scale-[0.99]'
        }`}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin text-black" />
            <span>Сегментация... ({elapsedSeconds.toFixed(1)} с)</span>
          </>
        ) : (
          <>
            <Play className="w-5 h-5 fill-current" />
            <span>Запустить сегментацию</span>
          </>
        )}
      </button>
    </div>
  );
};
