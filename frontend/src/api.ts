import type { HealthStatus, MetricsData, SampleItem, SegmentationResult, TaskType } from './types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchMetrics(task: TaskType): Promise<MetricsData> {
  const res = await fetch(`${API_BASE}/metrics/${task}`);
  if (!res.ok) {
    throw new Error(`Failed to load metrics for ${task}`);
  }
  return res.json();
}

export async function fetchSamples(): Promise<SampleItem[]> {
  const res = await fetch(`${API_BASE}/samples`);
  if (!res.ok) {
    throw new Error(`Failed to load sample images`);
  }
  return res.json();
}

export async function runSegmentation(
  fileOrBlob: File | Blob,
  fileName: string,
  task: TaskType,
  tta: boolean,
  opacity: number = 0.55
): Promise<SegmentationResult> {
  const formData = new FormData();
  formData.append('file', fileOrBlob, fileName);
  formData.append('task', task);
  formData.append('tta', String(tta));
  formData.append('opacity', String(opacity));

  const res = await fetch(`${API_BASE}/segment`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = `Segmentation failed with HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  const result: SegmentationResult = await res.json();
  result.id = `seg_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  result.timestamp = Date.now();
  return result;
}

export async function runSegmentationFromUrl(
  url: string,
  fileName: string,
  task: TaskType,
  tta: boolean,
  opacity: number = 0.55
): Promise<SegmentationResult> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch preset sample image from ${url}`);
  }
  const blob = await response.blob();
  return runSegmentation(blob, fileName, task, tta, opacity);
}
