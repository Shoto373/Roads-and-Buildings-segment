import React, { useState, useEffect } from 'react';
import {
  Plane,
  Satellite,
  Play,
  Loader2,
  Sparkles,
  ArrowRightLeft,
  Zap,
  Layers,
  Compass,
  Building2,
  AlertCircle
} from 'lucide-react';
import { ImageDropzone } from './ImageDropzone';
import { ComparisonViewer } from './ComparisonViewer';
import type { SampleItem, SegmentationResult } from '../types';
import { runSegmentation, runSegmentationFromUrl } from '../api';

interface DualWorkspaceProps {
  samples: SampleItem[];
  onAddToHistory: (result: SegmentationResult) => void;
}

export const DualWorkspace: React.FC<DualWorkspaceProps> = ({
  samples,
  onAddToHistory,
}) => {
  // Mode toggle: dual (split-screen 2 windows) vs single aerial vs single satellite
  const [layoutMode, setLayoutMode] = useState<'dual' | 'aerial' | 'satellite'>('dual');

  // ==========================================
  // Window 1: Aerial Photography (TIFF 1500x1500)
  // ==========================================
  const [aerialFile, setAerialFile] = useState<File | null>(null);
  const [aerialSample, setAerialSample] = useState<SampleItem | null>(null);
  const [aerialPreview, setAerialPreview] = useState<string | null>(null);
  const [aerialTask, setAerialTask] = useState<'road' | 'building'>('road');
  const [aerialTta, setAerialTta] = useState<boolean>(false);
  const [aerialOpacity, setAerialOpacity] = useState<number>(0.55);
  const [aerialLoading, setAerialLoading] = useState<boolean>(false);
  const [aerialElapsed, setAerialElapsed] = useState<number>(0);
  const [aerialResult, setAerialResult] = useState<SegmentationResult | null>(null);
  const [aerialError, setAerialError] = useState<string | null>(null);

  // ==========================================
  // Window 2: Satellite Imagery (DeepGlobe 1024x1024)
  // ==========================================
  const [satelliteFile, setSatelliteFile] = useState<File | null>(null);
  const [satelliteSample, setSatelliteSample] = useState<SampleItem | null>(null);
  const [satellitePreview, setSatellitePreview] = useState<string | null>(null);
  const [satelliteTta, setSatelliteTta] = useState<boolean>(false);
  const [satelliteOpacity, setSatelliteOpacity] = useState<number>(0.55);
  const [satelliteLoading, setSatelliteLoading] = useState<boolean>(false);
  const [satelliteElapsed, setSatelliteElapsed] = useState<number>(0);
  const [satelliteResult, setSatelliteResult] = useState<SegmentationResult | null>(null);
  const [satelliteError, setSatelliteError] = useState<string | null>(null);

  // Timers for inference
  useEffect(() => {
    let interval: any;
    if (aerialLoading) {
      setAerialElapsed(0);
      const start = performance.now();
      interval = setInterval(() => {
        setAerialElapsed((performance.now() - start) / 1000);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [aerialLoading]);

  useEffect(() => {
    let interval: any;
    if (satelliteLoading) {
      setSatelliteElapsed(0);
      const start = performance.now();
      interval = setInterval(() => {
        setSatelliteElapsed((performance.now() - start) / 1000);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [satelliteLoading]);

  // Handlers Window 1 (Aerial)
  const handleAerialFileSelect = (file: File | null) => {
    setAerialFile(file);
    setAerialSample(null);
    setAerialError(null);
    if (file) {
      setAerialPreview(URL.createObjectURL(file));
    } else {
      setAerialPreview(null);
    }
  };

  const handleAerialSampleSelect = (sample: SampleItem) => {
    setAerialSample(sample);
    setAerialFile(null);
    setAerialPreview(sample.url);
    if (sample.recommended_task === 'road' || sample.recommended_task === 'building') {
      setAerialTask(sample.recommended_task);
    }
    setAerialError(null);
  };

  const runAerialInference = async () => {
    if (!aerialFile && !aerialSample) return;
    setAerialLoading(true);
    setAerialError(null);
    try {
      let res: SegmentationResult;
      if (aerialFile) {
        res = await runSegmentation(aerialFile, aerialFile.name, aerialTask, aerialTta, aerialOpacity);
      } else if (aerialSample) {
        res = await runSegmentationFromUrl(aerialSample.url, `${aerialSample.id}.jpg`, aerialTask, aerialTta, aerialOpacity);
      } else {
        return;
      }
      setAerialResult(res);
      onAddToHistory(res);
    } catch (err: any) {
      setAerialError(err.message || 'Ошибка обработки аэроснимка');
    } finally {
      setAerialLoading(false);
    }
  };

  // Handlers Window 2 (Satellite)
  const handleSatelliteFileSelect = (file: File | null) => {
    setSatelliteFile(file);
    setSatelliteSample(null);
    setSatelliteError(null);
    if (file) {
      setSatellitePreview(URL.createObjectURL(file));
    } else {
      setSatellitePreview(null);
    }
  };

  const handleSatelliteSampleSelect = (sample: SampleItem) => {
    setSatelliteSample(sample);
    setSatelliteFile(null);
    setSatellitePreview(sample.url);
    setSatelliteError(null);
  };

  const runSatelliteInference = async () => {
    if (!satelliteFile && !satelliteSample) return;
    setSatelliteLoading(true);
    setSatelliteError(null);
    try {
      let res: SegmentationResult;
      if (satelliteFile) {
        res = await runSegmentation(satelliteFile, satelliteFile.name, 'satellite_road', satelliteTta, satelliteOpacity);
      } else if (satelliteSample) {
        res = await runSegmentationFromUrl(satelliteSample.url, `${satelliteSample.id}.jpg`, 'satellite_road', satelliteTta, satelliteOpacity);
      } else {
        return;
      }
      setSatelliteResult(res);
      onAddToHistory(res);
    } catch (err: any) {
      setSatelliteError(err.message || 'Ошибка обработки спутникового снимка');
    } finally {
      setSatelliteLoading(false);
    }
  };

  // Sync actions
  const runBothWindows = () => {
    if (aerialFile || aerialSample) {
      runAerialInference();
    }
    if (satelliteFile || satelliteSample) {
      runSatelliteInference();
    }
  };

  const loadDemoPair = () => {
    // Left: highway aerial sample
    const highway = samples.find((s) => s.id === 'sample-highway') || samples[0];
    if (highway) {
      handleAerialSampleSelect(highway);
    }
    // Right: satellite sample
    const sat = samples.find((s) => s.id === 'sample-satellite') || samples[samples.length - 1];
    if (sat) {
      handleSatelliteSampleSelect(sat);
    }
  };

  const copyAerialToSatellite = () => {
    if (aerialFile) {
      setSatelliteFile(aerialFile);
      setSatelliteSample(null);
      setSatellitePreview(aerialPreview);
    } else if (aerialSample) {
      setSatelliteSample(aerialSample);
      setSatelliteFile(null);
      setSatellitePreview(aerialSample.url);
    }
  };

  // Filter samples for each window
  const aerialSamples = samples.filter((s) => s.recommended_task !== 'satellite_road');
  const satelliteSamples = samples.filter((s) => s.id === 'sample-satellite' || s.recommended_task === 'satellite_road' || s.recommended_task === 'road');

  return (
    <div className="space-y-6">
      {/* Top Bar: View Mode Switcher and Quick Batch Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-4 backdrop-blur-md shadow-lg">
        {/* Left: View Mode Buttons */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setLayoutMode('dual')}
            className={`flex-1 sm:flex-initial px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-2 ${
              layoutMode === 'dual'
                ? 'bg-gradient-to-r from-cyan-500/20 to-amber-500/20 text-white border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <span className="flex h-2 w-2 rounded-full bg-cyan-400" />
            <span className="flex h-2 w-2 rounded-full bg-amber-400 -ml-1" />
            <span>Сплит-экран (2 окна)</span>
          </button>

          <button
            type="button"
            onClick={() => setLayoutMode('aerial')}
            className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
              layoutMode === 'aerial'
                ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Plane className="w-3.5 h-3.5 text-cyan-400" />
            <span>Аэрофото (1500×1500)</span>
          </button>

          <button
            type="button"
            onClick={() => setLayoutMode('satellite')}
            className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
              layoutMode === 'satellite'
                ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Satellite className="w-3.5 h-3.5 text-amber-400" />
            <span>Спутник (1024×1024)</span>
          </button>
        </div>

        {/* Right: Quick actions for 2 windows */}
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <button
            type="button"
            onClick={loadDemoPair}
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
            title="Загрузить тестовую пару: аэроснимок в окно 1 и спутниковый снимок в окно 2"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Загрузить демо-пару</span>
          </button>

          {layoutMode === 'dual' && (
            <>
              <button
                type="button"
                onClick={copyAerialToSatellite}
                disabled={!aerialFile && !aerialSample}
                className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                title="Скопировать снимок из левого окна в правое для сравнения моделей на одном кадре"
              >
                <ArrowRightLeft className="w-3.5 h-3.5 text-slate-400" />
                <span>Снимок 1 → 2</span>
              </button>

              <button
                type="button"
                onClick={runBothWindows}
                disabled={aerialLoading || satelliteLoading || (!aerialFile && !aerialSample && !satelliteFile && !satelliteSample)}
                className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-amber-600 hover:from-cyan-500 hover:to-amber-500 text-white font-semibold text-xs shadow-md shadow-cyan-900/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5 fill-current" />
                <span>Запустить оба окна</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Grid container: 1 or 2 columns based on layoutMode */}
      <div className={`grid grid-cols-1 ${layoutMode === 'dual' ? 'xl:grid-cols-2' : ''} gap-6 items-start`}>
        {/* ======================================================== */}
        {/* WINDOW 1: AERIAL (MASSACHUSETTS TIFF 1500x1500)         */}
        {/* ======================================================== */}
        {(layoutMode === 'dual' || layoutMode === 'aerial') && (
          <div className="bg-slate-900/50 border border-cyan-500/30 rounded-3xl p-5 sm:p-6 space-y-5 backdrop-blur-md relative shadow-xl shadow-cyan-950/20">
            {/* Window Header */}
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-sm">
                  <Plane className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-bold text-white text-base">Окно 1: Аэрофотосъемка (БПЛА)</h2>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                      TIFF 1500×1500
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Massachusetts Dataset • Модель EfficientNet-B7 UNet (Ортофотопланы)
                  </p>
                </div>
              </div>

              {/* Task toggle: Road / Building */}
              <div className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => setAerialTask('road')}
                  disabled={aerialLoading}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    aerialTask === 'road'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Compass className="w-3.5 h-3.5" />
                  <span>Дороги</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAerialTask('building')}
                  disabled={aerialLoading}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    aerialTask === 'building'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Здания</span>
                </button>
              </div>
            </div>

            {/* Error banner */}
            {aerialError && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
                <span>{aerialError}</span>
              </div>
            )}

            {/* View Result or Input */}
            {aerialResult ? (
              <div className="space-y-4">
                <ComparisonViewer
                  result={aerialResult}
                  onReset={() => {
                    setAerialResult(null);
                    setAerialFile(null);
                    setAerialSample(null);
                    setAerialPreview(null);
                  }}
                />
              </div>
            ) : (
              <div className="space-y-4">
                {/* Dropzone for Aerial */}
                <ImageDropzone
                  selectedFile={aerialFile}
                  onFileSelect={handleAerialFileSelect}
                  samples={aerialSamples}
                  onSelectSample={handleAerialSampleSelect}
                  selectedSampleId={aerialSample?.id || null}
                  previewUrl={aerialPreview}
                  disabled={aerialLoading}
                  modeTitle="Перетащите снимок TIFF / PNG сюда или "
                  modeSubtitle="Оптимизировано для аэрофото 1500×1500 (TIFF, PNG, JPG) • До 30 МБ"
                  themeColor="cyan"
                  compact={layoutMode === 'dual'}
                />

                {/* Inference Options Bar */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                  {/* Opacity slider & TTA */}
                  <div className="flex flex-wrap items-center gap-4 w-full sm:w-auto">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-medium whitespace-nowrap">Прозрачность:</span>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.05"
                        value={aerialOpacity}
                        onChange={(e) => setAerialOpacity(parseFloat(e.target.value))}
                        className="w-24 accent-cyan-400 cursor-pointer"
                      />
                      <span className="text-xs font-mono text-cyan-300">{Math.round(aerialOpacity * 100)}%</span>
                    </div>

                    <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
                      <input
                        type="checkbox"
                        checked={aerialTta}
                        onChange={(e) => setAerialTta(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                      />
                      <span>TTA</span>
                    </label>
                  </div>

                  {/* Run Button */}
                  <button
                    type="button"
                    onClick={runAerialInference}
                    disabled={aerialLoading || (!aerialFile && !aerialSample)}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-xs tracking-wide uppercase transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {aerialLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-black" />
                        <span>Сегментация... {aerialElapsed.toFixed(1)}с</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-black" />
                        <span>Сегментировать аэроснимок</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* WINDOW 2: SATELLITE (DEEPGLOBE 1024x1024 DEEPLABV3+)     */}
        {/* ======================================================== */}
        {(layoutMode === 'dual' || layoutMode === 'satellite') && (
          <div className="bg-slate-900/50 border border-amber-500/30 rounded-3xl p-5 sm:p-6 space-y-5 backdrop-blur-md relative shadow-xl shadow-amber-950/20">
            {/* Window Header */}
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-sm">
                  <Satellite className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-bold text-white text-base">Окно 2: Спутниковая съемка</h2>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800">
                      1024×1024 DeepGlobe
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    DigitalGlobe Satellites • Модель DeepLabV3+ с ASPP (Орбитальные снимки)
                  </p>
                </div>
              </div>

              {/* Architecture Badge */}
              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs font-semibold">
                <Layers className="w-3.5 h-3.5 text-amber-400" />
                <span>DeepLabV3+ ASPP</span>
              </div>
            </div>

            {/* Error banner */}
            {satelliteError && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
                <span>{satelliteError}</span>
              </div>
            )}

            {/* View Result or Input */}
            {satelliteResult ? (
              <div className="space-y-4">
                <ComparisonViewer
                  result={satelliteResult}
                  onReset={() => {
                    setSatelliteResult(null);
                    setSatelliteFile(null);
                    setSatelliteSample(null);
                    setSatellitePreview(null);
                  }}
                />
              </div>
            ) : (
              <div className="space-y-4">
                {/* Dropzone for Satellite */}
                <ImageDropzone
                  selectedFile={satelliteFile}
                  onFileSelect={handleSatelliteFileSelect}
                  samples={satelliteSamples}
                  onSelectSample={handleSatelliteSampleSelect}
                  selectedSampleId={satelliteSample?.id || null}
                  previewUrl={satellitePreview}
                  disabled={satelliteLoading}
                  modeTitle="Перетащите спутниковый снимок сюда или "
                  modeSubtitle="Оптимизировано для снимков со спутника 1024×1024 (JPG, PNG, GeoTIFF) • До 30 МБ"
                  themeColor="amber"
                  compact={layoutMode === 'dual'}
                />

                {/* Inference Options Bar */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                  {/* Opacity slider & TTA */}
                  <div className="flex flex-wrap items-center gap-4 w-full sm:w-auto">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-medium whitespace-nowrap">Прозрачность:</span>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.05"
                        value={satelliteOpacity}
                        onChange={(e) => setSatelliteOpacity(parseFloat(e.target.value))}
                        className="w-24 accent-amber-400 cursor-pointer"
                      />
                      <span className="text-xs font-mono text-amber-300">{Math.round(satelliteOpacity * 100)}%</span>
                    </div>

                    <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
                      <input
                        type="checkbox"
                        checked={satelliteTta}
                        onChange={(e) => setSatelliteTta(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900 text-amber-500 focus:ring-0"
                      />
                      <span>TTA</span>
                    </label>
                  </div>

                  {/* Run Button */}
                  <button
                    type="button"
                    onClick={runSatelliteInference}
                    disabled={satelliteLoading || (!satelliteFile && !satelliteSample)}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black font-bold text-xs tracking-wide uppercase transition-all shadow-lg shadow-amber-500/20 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {satelliteLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-black" />
                        <span>Сегментация... {satelliteElapsed.toFixed(1)}с</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-black" />
                        <span>Сегментировать спутниковый снимок</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
