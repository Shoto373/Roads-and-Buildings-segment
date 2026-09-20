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
}

export const ImageDropzone: React.FC<ImageDropzoneProps> = ({
  selectedFile,
  onFileSelect,
  samples,
  onSelectSample,
  selectedSampleId,
  previewUrl,
  disabled,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSetFile = (file: File) => {
    setErrorMsg(null);
    const validExtensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValid) {
      setErrorMsg(`Неподдерживаемый формат файла. Допустимы: ${validExtensions.join(', ')}`);
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
    <div className="space-y-4">
      {/* Upload Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && !selectedFile && !selectedSampleId && fileInputRef.current?.click()}
        className={`relative rounded-2xl border-2 border-dashed p-6 transition-all duration-200 text-center ${
          disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
        } ${
          isDragOver
            ? 'border-cyan-400 bg-cyan-950/20'
            : selectedFile || selectedSampleId
            ? 'border-cyan-500/40 bg-slate-900/60'
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
            <div className="relative group rounded-xl overflow-hidden border border-slate-700 max-h-64 shadow-xl">
              <img
                src={previewUrl}
                alt="Selected aerial view"
                className="max-h-64 object-contain rounded-lg"
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
            <div className="mt-3 text-xs text-slate-400 flex items-center gap-2">
              <span className="font-medium text-slate-200">
                {selectedFile?.name || 'Предустановленный снимок'}
              </span>
              {selectedFile && (
                <span>({(selectedFile.size / (1024 * 1024)).toFixed(2)} МБ)</span>
              )}
            </div>
          </div>
        ) : (
          /* Empty / Upload prompt */
          <div className="py-6 flex flex-col items-center justify-center space-y-3">
            <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Перетащите аэрофотоснимок сюда или{' '}
                <span className="text-cyan-400 hover:underline">выберите на диске</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Поддерживаются PNG, JPG, JPEG, TIFF • До 30 МБ • Произвольное разрешение
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
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>Или протестируйте на готовых снимках (1 клик):</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {samples.map((sample) => {
              const isSelected = selectedSampleId === sample.id;
              return (
                <button
                  key={sample.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelectSample(sample)}
                  className={`group relative text-left p-2 rounded-lg border transition-all text-xs flex flex-col ${
                    isSelected
                      ? 'border-cyan-400 bg-cyan-950/30 ring-1 ring-cyan-400'
                      : 'border-slate-800 hover:border-slate-600 bg-slate-950/50 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="relative aspect-square w-full rounded overflow-hidden bg-slate-900 mb-2">
                    <img
                      src={sample.thumbnail}
                      alt={sample.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    {isSelected && (
                      <div className="absolute top-1 right-1 bg-cyan-500 text-black p-0.5 rounded-full shadow">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </div>
                    )}
                    <span
                      className={`absolute bottom-1 left-1 text-[9px] font-bold uppercase px-1 py-0.2 rounded backdrop-blur-sm ${
                        sample.recommended_task === 'road'
                          ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800'
                          : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {sample.recommended_task === 'road' ? 'Дороги' : 'Здания'}
                    </span>
                  </div>
                  <span className="font-medium text-slate-200 truncate w-full">
                    {sample.title}
                  </span>
                  <span className="text-[10px] text-slate-400 truncate w-full">
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
