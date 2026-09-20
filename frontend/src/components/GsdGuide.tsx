import React from 'react';
import { Compass, CheckCircle2, AlertTriangle, XCircle, Sparkles } from 'lucide-react';

export const GsdGuide: React.FC = () => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2">
      {/* Title block */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold mb-2">
          <Compass className="w-5 h-5" />
          <span>Руководство по пространственному разрешению (GSD)</span>
        </div>
        <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
          <strong>GSD (Ground Sample Distance)</strong> — физическое расстояние на поверхности Земли, соответствующее размеру одного пикселя на снимке. Для корректной работы нейросети важно соответствие масштаба обучающей выборке.
        </p>
      </div>

      {/* 3 Categories: Optimal, Drone, Satellite */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Optimal */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-emerald-500/30 space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
            <CheckCircle2 className="w-5 h-5" />
            <span>Оптимально (1.0 м/пикс)</span>
          </div>
          <p className="text-xs text-slate-300">
            Ортофотопланы и государственная аэрофотосъемка (USGS, MassGIS, Росреестр).
          </p>
          <div className="p-3 rounded-xl bg-slate-950/70 text-xs space-y-1 font-mono">
            <div className="text-slate-400">Диапазон: <span className="text-white">0.5 – 1.5 м/пикс</span></div>
            <div className="text-slate-400">Ширина дороги: <span className="text-emerald-400">6–8 пикселей</span></div>
            <div className="text-slate-400">Статус: <span className="text-emerald-400 font-bold">100% готовность</span></div>
          </div>
          <p className="text-[11px] text-slate-400 leading-normal">
            Идеальный масштаб. Модель обучена именно на таких снимках и выдает максимальную точность.
          </p>
        </div>

        {/* Card 2: Drone */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-amber-500/30 space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl" />
          <div className="flex items-center gap-2 text-amber-400 font-bold text-sm">
            <AlertTriangle className="w-5 h-5" />
            <span>Дроны и БПЛА (&lt;0.1 м/пикс)</span>
          </div>
          <p className="text-xs text-slate-300">
            Сверхвысокая детализация с квадрокоптеров (DJI, Геоскан и др.).
          </p>
          <div className="p-3 rounded-xl bg-slate-950/70 text-xs space-y-1 font-mono">
            <div className="text-slate-400">Диапазон: <span className="text-white">0.03 – 0.15 м/пикс</span></div>
            <div className="text-slate-400">Ширина дороги: <span className="text-amber-400">50–150 пикселей</span></div>
            <div className="text-slate-400">Действие: <span className="text-amber-400 font-bold">Сжатие в 5–10×</span></div>
          </div>
          <p className="text-[11px] text-slate-400 leading-normal">
            <strong>Обязательно:</strong> перед подачей в модель уменьшите снимок (downscale) в 5–10 раз, иначе широкая дорога будет распознана как пустое поле.
          </p>
        </div>

        {/* Card 3: Satellite */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-red-500/30 space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 rounded-full blur-2xl" />
          <div className="flex items-center gap-2 text-red-400 font-bold text-sm">
            <XCircle className="w-5 h-5" />
            <span>Спутники (10–30 м/пикс)</span>
          </div>
          <p className="text-xs text-slate-300">
            Бесплатные спутники Sentinel-2, Landsat-8, метеорологические зонды.
          </p>
          <div className="p-3 rounded-xl bg-slate-950/70 text-xs space-y-1 font-mono">
            <div className="text-slate-400">Диапазон: <span className="text-white">10 – 30 м/пикс</span></div>
            <div className="text-slate-400">Ширина дороги: <span className="text-red-400">&lt;1 пикселя</span></div>
            <div className="text-slate-400">Статус: <span className="text-red-400 font-bold">Непригодно</span></div>
          </div>
          <p className="text-[11px] text-slate-400 leading-normal">
            Физическое разрешение не позволяет различить дорогу или контур дома, так как весь объект тоньше одного пикселя.
          </p>
        </div>
      </div>

      {/* Practical tips */}
      <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
        <div className="flex items-center gap-2 text-white text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>Технические рекомендации по подготовке файлов</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-400">
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/60">
            <span className="font-semibold text-slate-200">Любые габариты в пикселях:</span>
            <p className="mt-1">
              Бэкенд автоматически дополняет кадр симметричным отражением до кратности 32 и возвращает маску в исходном разрешении.
            </p>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/60">
            <span className="font-semibold text-slate-200">Сверхбольшие ортофотопланы:</span>
            <p className="mt-1">
              Для изображений крупнее 4000×4000 пикселей рекомендуется нарезка на тайлы 1500×1500 с нахлестом 64 пикселя для экономии видеопамяти.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
