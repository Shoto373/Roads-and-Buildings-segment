import React, { useRef, useState } from 'react';
import { UploadCloud, X, Sparkles, CheckCircle2 } from 'lucide-react';
import type { SampleItem } from '../types';

interface ImageDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  samples: SampleItem[];
  onSelectSample: (sample: SampleItem) => void;
  selectedSampleId: string | null;
  previewUrl: string | null;
  disabled: boolean;
  modeTitle?: string;
  modeSubtitle?: string;
  themeColor?: 'cyan' | 'amber' | 'emerald';
  compact?: boolean;
}

export const ImageDropzone: React.FC<ImageDropzoneProps> = ({
  selectedFile,
  onFileSelect,
  samples,
  onSelectSample,
  selectedSampleId,
  previewUrl,
  disabled,
  modeTitle,
  modeSubtitle,
  themeColor = 'cyan',
  compact = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isAmber = themeColor === 'amber';
  const isEmerald = themeColor === 'emerald';

  const activeBorderClass = isAmber
    ? 'border-amber-400 bg-amber-950/20'
    : isEmerald
    ? 'border-emerald-400 bg-emerald-950/20'
    : 'border-cyan-400 bg-cyan-950/20';

  const activeSelectedBorder = isAmber
    ? 'border-amber-500/50 bg-slate-900/60'
    : isEmerald
    ? 'border-emerald-500/50 bg-slate-900/60'
    : 'border-cyan-500/50 bg-slate-900/60';

  const iconTextClass = isAmber
    ? 'text-amber-400'
    : isEmerald
    ? 'text-emerald-400'
    : 'text-cyan-400';

  const linkTextClass = isAmber
    ? 'text-amber-400'
    : isEmerald
    ? 'text-emerald-400'
    : 'text-cyan-400';

  const validateAndSetFile = (file: File) => {
    setErrorMsg(null);
    const validExtensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValid) {
      setErrorMsg(`Неподдерживаемый формат. Допустимы: ${validExtensions.join(', ')}`);
      return;
    }

    if (file.size > 30 * 1024 * 1024) {
      setErrorMsg('Размер файла превышает лимит 30 МБ.');
      return;
    }

    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-3">
      {/* Upload Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && !selectedFile && !selectedSampleId && fileInputRef.current?.click()}
        className={`relative rounded-2xl border-2 border-dashed ${compact ? 'p-4' : 'p-6'} transition-all duration-200 text-center ${
          disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
        } ${
          isDragOver
            ? activeBorderClass
            : selectedFile || selectedSampleId
            ? activeSelectedBorder
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/40 hover:bg-slate-900/70'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.tif,.tiff"
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled}
        />

        {previewUrl ? (
          /* Preview Mode */
          <div className="flex flex-col items-center">
            <div className={`relative group rounded-xl overflow-hidden border border-slate-700 ${compact ? 'max-h-48' : 'max-h-64'} shadow-xl`}>
              <img
                src={previewUrl}
                alt="Selected view"
                className={`${compact ? 'max-h-48' : 'max-h-64'} object-contain rounded-lg`}
              />
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onFileSelect(null);
                }}
                disabled={disabled}
                className="absolute top-2 right-2 p-1.5 rounded-full bg-black/70 hover:bg-red-600 text-white transition-colors backdrop-blur-sm"
                title="Удалить снимок"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-2 text-xs text-slate-400 flex items-center gap-2">
              <span className="font-medium text-slate-200 truncate max-w-xs">
                {selectedFile?.name || 'Предустановленный снимок'}
              </span>
              {selectedFile && (
                <span>({(selectedFile.size / (1024 * 1024)).toFixed(2)} МБ)</span>
              )}
            </div>
          </div>
        ) : (
          /* Empty / Upload prompt */
          <div className={`${compact ? 'py-3 space-y-2' : 'py-5 space-y-3'} flex flex-col items-center justify-center`}>
            <div className={`${compact ? 'w-10 h-10' : 'w-12 h-12'} rounded-full bg-slate-800 flex items-center justify-center ${iconTextClass} group-hover:scale-105 transition-transform`}>
              <UploadCloud className={`${compact ? 'w-5 h-5' : 'w-6 h-6'}`} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                {modeTitle ? modeTitle : 'Перетащите снимок сюда или '}{' '}
                <span className={`${linkTextClass} hover:underline`}>выберите на диске</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {modeSubtitle || 'Поддерживаются PNG, JPG, TIFF • До 30 МБ'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {errorMsg && (
        <div className="p-3 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-xs flex items-center gap-2">
          <X className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Quick Sample Presets */}
      {samples.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-2">
            <Sparkles className={`w-3.5 h-3.5 ${iconTextClass}`} />
            <span>Примеры снимков для быстрого теста:</span>
          </div>

          <div className={`grid ${compact ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2 sm:grid-cols-4'} gap-2`}>
            {samples.map((sample) => {
              const isSelected = selectedSampleId === sample.id;
              return (
                <button
                  key={sample.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelectSample(sample)}
                  className={`group relative text-left p-1.5 rounded-lg border transition-all text-xs flex flex-col ${
                    isSelected
                      ? isAmber
                        ? 'border-amber-400 bg-amber-950/30 ring-1 ring-amber-400'
                        : 'border-cyan-400 bg-cyan-950/30 ring-1 ring-cyan-400'
                      : 'border-slate-800 hover:border-slate-600 bg-slate-950/50 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="relative aspect-square w-full rounded overflow-hidden bg-slate-900 mb-1.5">
                    <img
                      src={sample.thumbnail}
                      alt={sample.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    {isSelected && (
                      <div className={`absolute top-1 right-1 ${isAmber ? 'bg-amber-500' : 'bg-cyan-500'} text-black p-0.5 rounded-full shadow`}>
                        <CheckCircle2 className="w-3 h-3" />
                      </div>
                    )}
                    <span
                      className={`absolute bottom-1 left-1 text-[8px] font-bold uppercase px-1 py-0.2 rounded backdrop-blur-sm ${
                        sample.recommended_task === 'satellite_road'
                          ? 'bg-amber-950/90 text-amber-300 border border-amber-800'
                          : sample.recommended_task === 'road'
                          ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800'
                          : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {sample.recommended_task === 'satellite_road'
                        ? 'Спутник'
                        : sample.recommended_task === 'road'
                        ? 'Дороги'
                        : 'Здания'}
                    </span>
                  </div>
                  <span className="font-medium text-slate-200 truncate w-full text-[11px]">
                    {sample.title}
                  </span>
                  <span className="text-[9px] text-slate-400 truncate w-full">
                    {sample.description}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
