import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DualWorkspace } from './components/DualWorkspace';
import { MetricsView } from './components/MetricsView';
import { GsdGuide } from './components/GsdGuide';
import { HistoryDrawer } from './components/HistoryDrawer';
import { ComparisonViewer } from './components/ComparisonViewer';
import type { HealthStatus, SampleItem, SegmentationResult } from './types';
import { fetchHealth, fetchSamples } from './api';
import { AlertCircle, X } from 'lucide-react';

const STORAGE_KEY = 'aerial_segnet_history_v1';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'segment' | 'metrics' | 'guide'>('segment');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [samples, setSamples] = useState<SampleItem[]>([]);

  // History & Modal Inspection
  const [history, setHistory] = useState<SegmentationResult[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [historyModalResult, setHistoryModalResult] = useState<SegmentationResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const handleAddToHistory = (result: SegmentationResult) => {
    setHistory((prev) => [result, ...prev.slice(0, 9)]);
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

        {/* TAB 1: DUAL WORKSPACE (Side-by-Side: Aerial 1500x1500 & Satellite 1024x1024) */}
        {activeTab === 'segment' && (
          <DualWorkspace
            samples={samples}
            onAddToHistory={handleAddToHistory}
          />
        )}

        {/* TAB 2: METRICS & BENCHMARKS */}
        {activeTab === 'metrics' && <MetricsView />}

        {/* TAB 3: GSD & RESOLUTION GUIDE */}
        {activeTab === 'guide' && <GsdGuide />}
      </main>

      {/* Modal for viewing saved history item */}
      {historyModalResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-5xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-5">
              <div>
                <h3 className="text-lg font-bold text-white">Просмотр результата из истории</h3>
                <p className="text-xs text-slate-400">{historyModalResult.filename}</p>
              </div>
              <button
                type="button"
                onClick={() => setHistoryModalResult(null)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <ComparisonViewer
              result={historyModalResult}
              onReset={() => setHistoryModalResult(null)}
            />
          </div>
        </div>
      )}

      {/* History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelectResult={(res) => {
          setHistoryModalResult(res);
          setIsHistoryOpen(false);
        }}
        onClearHistory={() => {
          setHistory([]);
          localStorage.removeItem(STORAGE_KEY);
        }}
      />
    </div>
  );
};

export default App;
