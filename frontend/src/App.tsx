import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ImageDropzone } from './components/ImageDropzone';
import { InferenceControls } from './components/InferenceControls';
import { ComparisonViewer } from './components/ComparisonViewer';
import { MetricsView } from './components/MetricsView';
import { GsdGuide } from './components/GsdGuide';
import { HistoryDrawer } from './components/HistoryDrawer';
import type {
  HealthStatus,
  SampleItem,
  SegmentationResult,
  TaskType,
} from './types';
import {
  fetchHealth,
  fetchSamples,
  runSegmentation,
  runSegmentationFromUrl,
} from './api';
import { AlertCircle } from 'lucide-react';

const STORAGE_KEY = 'aerial_segnet_history_v1';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'segment' | 'metrics' | 'guide'>('segment');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [samples, setSamples] = useState<SampleItem[]>([]);

  // Selection & Parameters
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSample, setSelectedSample] = useState<SampleItem | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [task, setTask] = useState<TaskType>('road');
  const [tta, setTta] = useState<boolean>(false);
  const [opacity, setOpacity] = useState<number>(0.55);

  // Execution state
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Results & History
  const [currentResult, setCurrentResult] = useState<SegmentationResult | null>(null);
  const [history, setHistory] = useState<SegmentationResult[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);

  // Load initial health, samples, and localStorage history
  useEffect(() => {
    async function init() {
      try {
        const h = await fetchHealth();
        setHealth(h);
      } catch (err) {
        console.warn('Failed to load initial health:', err);
      }

      try {
        const s = await fetchSamples();
        setSamples(s);
      } catch (err) {
        console.warn('Failed to load samples:', err);
      }

      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            setHistory(parsed.slice(0, 10)); // keep last 10
          }
        }
      } catch {
        // ignore storage parse errors
      }
    }
    init();
  }, []);

  // Save history to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 10)));
    } catch {
      // ignore storage quota errors
    }
  }, [history]);

  // Elapsed timer during inference
  useEffect(() => {
    let interval: any;
    if (isLoading) {
      setElapsedSeconds(0);
      const startTime = performance.now();
      interval = setInterval(() => {
        setElapsedSeconds((performance.now() - startTime) / 1000);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setSelectedSample(null);
    setErrorMessage(null);
    if (file) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleSelectSample = (sample: SampleItem) => {
    setSelectedSample(sample);
    setSelectedFile(null);
    setPreviewUrl(sample.url);
    setTask(sample.recommended_task);
    setErrorMessage(null);
  };

  const handleRunSegmentation = async () => {
    if (!selectedFile && !selectedSample) {
      setErrorMessage('Пожалуйста, выберите снимок или воспользуйтесь готовым образцом.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      let result: SegmentationResult;
      if (selectedFile) {
        result = await runSegmentation(selectedFile, selectedFile.name, task, tta, opacity);
      } else if (selectedSample) {
        result = await runSegmentationFromUrl(
          selectedSample.url,
          `${selectedSample.id}.jpg`,
          task,
          tta,
          opacity
        );
      } else {
        throw new Error('No image specified');
      }

      setCurrentResult(result);
      setHistory((prev) => [result, ...prev.filter((item) => item.id !== result.id)].slice(0, 10));
    } catch (err: any) {
      setErrorMessage(err.message || 'Произошла непредвиденная ошибка при инференсе.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentResult(null);
    setSelectedFile(null);
    setSelectedSample(null);
    setPreviewUrl(null);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-200 flex flex-col">
      {/* Header */}
      <Header
        health={health}
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setErrorMessage(null);
        }}
        historyCount={history.length}
        onOpenHistory={() => setIsHistoryOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error notification banner */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/60 border border-red-800/80 text-red-300 text-xs sm:text-sm flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-400 hover:text-white text-xs underline font-semibold ml-4"
            >
              Закрыть
            </button>
          </div>
        )}

        {/* TAB 1: SEGMENTATION SCREEN */}
        {activeTab === 'segment' && (
          <div>
            {currentResult ? (
              /* RESULT VIEW */
              <ComparisonViewer result={currentResult} onReset={handleReset} />
            ) : (
              /* INPUT & CONFIG VIEW */
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left col: Dropzone & Samples (7 cols) */}
                <div className="lg:col-span-7">
                  <ImageDropzone
                    selectedFile={selectedFile}
                    onFileSelect={handleFileSelect}
                    samples={samples}
                    onSelectSample={handleSelectSample}
                    selectedSampleId={selectedSample?.id || null}
                    previewUrl={previewUrl}
                    disabled={isLoading}
                  />
                </div>

                {/* Right col: Controls & Launch (5 cols) */}
                <div className="lg:col-span-5">
                  <InferenceControls
                    task={task}
                    setTask={setTask}
                    tta={tta}
                    setTta={setTta}
                    opacity={opacity}
                    setOpacity={setOpacity}
                    onRun={handleRunSegmentation}
                    isLoading={isLoading}
                    elapsedSeconds={elapsedSeconds}
                    disabled={!selectedFile && !selectedSample}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: METRICS & BENCHMARKS */}
        {activeTab === 'metrics' && <MetricsView />}

        {/* TAB 3: GSD & RESOLUTION GUIDE */}
        {activeTab === 'guide' && <GsdGuide />}
      </main>

      {/* History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelectResult={(res) => {
          setCurrentResult(res);
          setActiveTab('segment');
        }}
        onClearHistory={() => {
          setHistory([]);
          localStorage.removeItem(STORAGE_KEY);
        }}
      />

      {/* Subtle Footer */}
      <footer className="border-t border-slate-900 py-4 text-center text-xs text-slate-500">
        EfficientNet-B7 + UNet • Combo Loss • PyTorch AMP • GSD ~1.0 м/пикс
      </footer>
    </div>
  );
};

export default App;
