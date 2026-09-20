import React, { useState, useRef, useEffect } from 'react';
import {
  Download,
  Sliders,
  RotateCcw,
  Zap,
  Maximize2,
  Columns,
  Layers,
  Image as ImageIcon,
  CheckCircle2
} from 'lucide-react';
import type { SegmentationResult } from '../types';

interface ComparisonViewerProps {
  result: SegmentationResult;
  onReset: () => void;
}

type ViewMode = 'slider' | 'overlay' | 'mask' | 'original' | 'side-by-side';

export const ComparisonViewer: React.FC<ComparisonViewerProps> = ({ result, onReset }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('slider');
  const [sliderPosition, setSliderPosition] = useState<number>(50); // percentage 0-100
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Drag handlers for the Before/After split slider
  const handleMove = (clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(percentage);
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (!isDragging) return;
    handleMove(e.touches[0].clientX);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;
    handleMove(e.clientX);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('touchmove', handleTouchMove);
      window.addEventListener('touchend', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleMouseUp);
    };
  }, [isDragging]);

  const downloadImage = (dataUri: string, filename: string) => {
    const link = document.createElement('a');
    link.href = dataUri;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const baseFileName = result.filename
    ? result.filename.replace(/\.[^/.]+$/, '')
    : 'aerial_segmented';

  return (
    <div className="space-y-6">
      {/* Top action bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 rounded-2xl p-3 sm:p-4">
        {/* View Mode Pills */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setViewMode('slider')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'slider'
                ? 'bg-cyan-500 text-black font-semibold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Шторка</span>
          </button>
          <button
            onClick={() => setViewMode('overlay')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'overlay'
                ? 'bg-cyan-500 text-black font-semibold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Оверлей</span>
          </button>
          <button
            onClick={() => setViewMode('mask')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'mask'
                ? 'bg-cyan-500 text-black font-semibold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Маска</span>
          </button>
          <button
            onClick={() => setViewMode('side-by-side')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all hidden sm:flex items-center gap-1.5 ${
              viewMode === 'side-by-side'
                ? 'bg-cyan-500 text-black font-semibold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Рядом</span>
          </button>
          <button
            onClick={() => setViewMode('original')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'original'
                ? 'bg-cyan-500 text-black font-semibold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>Оригинал</span>
          </button>
        </div>

        {/* Download & Reset actions */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => downloadImage(result.images.mask, `${baseFileName}_${result.task}_mask.png`)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors"
            title="Скачать бинарную маску (PNG)"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Скачать</span> Маску
          </button>
          <button
            onClick={() => downloadImage(result.images.overlay, `${baseFileName}_${result.task}_overlay.png`)}
            className="px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-medium border border-cyan-500/30 flex items-center gap-1.5 transition-colors"
            title="Скачать снимок с наложенным оверлеем (PNG)"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Скачать</span> Оверлей
          </button>
          <button
            onClick={onReset}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors"
            title="Обработать другое изображение"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Новый снимок</span>
          </button>
        </div>
      </div>

      {/* Main Interactive Canvas / Image Display Container */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center min-h-[420px] shadow-2xl">
        {/* MODE 1: BEFORE / AFTER SPLIT SLIDER */}
        {viewMode === 'slider' && (
          <div
            ref={containerRef}
            className="relative w-full aspect-auto max-h-[650px] overflow-hidden select-none cursor-ew-resize flex items-center justify-center"
            onMouseDown={(e) => {
              setIsDragging(true);
              handleMove(e.clientX);
            }}
            onTouchStart={(e) => {
              setIsDragging(true);
              handleMove(e.touches[0].clientX);
            }}
          >
            {/* Background image: Segmented Overlay */}
            <img
              src={result.images.overlay}
              alt="Segmented Overlay"
              className="w-full h-auto max-h-[650px] object-contain block pointer-events-none"
            />

            {/* Foreground image: Original (clipped by percentage) */}
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none flex items-center justify-center"
              style={{ clipPath: `polygon(0 0, ${sliderPosition}% 0, ${sliderPosition}% 100%, 0 100%)` }}
            >
              <img
                src={result.images.original}
                alt="Original Aerial"
                className="w-full h-auto max-h-[650px] object-contain block pointer-events-none"
              />
            </div>

            {/* Slider Divider Line */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-cyan-400 shadow-[0_0_10px_#00E5FF] pointer-events-none"
              style={{ left: `${sliderPosition}%` }}
            >
              {/* Central handle knob */}
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-cyan-400 text-black flex items-center justify-center shadow-xl border-2 border-white">
                <Sliders className="w-4 h-4 rotate-90" />
              </div>
            </div>

            {/* Floating Labels */}
            <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-[11px] font-semibold text-slate-200 pointer-events-none border border-white/10">
              Оригинал
            </div>
            <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-[11px] font-semibold text-cyan-300 pointer-events-none border border-cyan-500/30">
              Сегментация ({result.task === 'road' ? 'Дороги' : 'Здания'})
            </div>
          </div>
        )}

        {/* MODE 2: OVERLAY VIEW */}
        {viewMode === 'overlay' && (
          <div className="relative w-full flex items-center justify-center p-2">
            <img
              src={result.images.overlay}
              alt="Overlay Result"
              className="w-full h-auto max-h-[650px] object-contain rounded-lg"
            />
          </div>
        )}

        {/* MODE 3: MASK ONLY */}
        {viewMode === 'mask' && (
          <div className="relative w-full flex items-center justify-center p-2 bg-black">
            <img
              src={result.images.mask}
              alt="Binary Mask"
              className="w-full h-auto max-h-[650px] object-contain rounded-lg"
            />
          </div>
        )}

        {/* MODE 4: ORIGINAL ONLY */}
        {viewMode === 'original' && (
          <div className="relative w-full flex items-center justify-center p-2">
            <img
              src={result.images.original}
              alt="Original Aerial"
              className="w-full h-auto max-h-[650px] object-contain rounded-lg"
            />
          </div>
        )}

        {/* MODE 5: SIDE-BY-SIDE */}
        {viewMode === 'side-by-side' && (
          <div className="grid grid-cols-2 gap-2 p-3 w-full">
            <div className="relative rounded-xl overflow-hidden border border-slate-800">
              <img
                src={result.images.original}
                alt="Original"
                className="w-full h-auto object-contain"
              />
              <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/70 text-[10px] text-white">
                Оригинал
              </span>
            </div>
            <div className="relative rounded-xl overflow-hidden border border-slate-800">
              <img
                src={result.images.overlay}
                alt="Overlay"
                className="w-full h-auto object-contain"
              />
              <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-[10px] text-cyan-300">
                Сегментация
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Telemetry & Statistics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Card 1: Time */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Время инференса</span>
          </div>
          <div className="text-lg font-bold text-white font-mono">
            {result.telemetry.inference_time_ms} <span className="text-xs font-normal text-slate-400">мс</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            Всего: {result.telemetry.total_time_ms} мс • {result.telemetry.device.toUpperCase()}
          </div>
        </div>

        {/* Card 2: Coverage */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Площадь покрытия</span>
          </div>
          <div className="text-lg font-bold text-cyan-400 font-mono">
            {result.statistics.coverage_percent}%
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {result.statistics.detected_pixels.toLocaleString()} пикселей
          </div>
        </div>

        {/* Card 3: Dimensions */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Maximize2 className="w-3.5 h-3.5 text-blue-400" />
            <span>Разрешение кадра</span>
          </div>
          <div className="text-lg font-bold text-white font-mono">
            {result.dimensions.width}×{result.dimensions.height}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            Паддинг до кратного 32
          </div>
        </div>

        {/* Card 4: Model & TTA */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span>Задача & Режим</span>
          </div>
          <div className="text-sm font-bold text-white uppercase tracking-wider">
            {result.task === 'road' ? 'Дороги' : 'Здания'}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            TTA: {result.tta ? 'Включен (3x)' : 'Выключен'}
          </div>
        </div>
      </div>
    </div>
  );
};
