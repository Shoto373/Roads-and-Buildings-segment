export type TaskType = 'road' | 'building' | 'satellite_road';

export interface HealthStatus {
  status: 'ready' | 'degraded' | 'error';
  device: string;
  road_model_loaded: boolean;
  building_model_loaded: boolean;
  satellite_model_loaded?: boolean;
  road_weights?: string;
  building_weights?: string;
  satellite_weights?: string;
  cuda?: {
    cuda_device_name?: string;
    allocated_memory_mb?: number;
    reserved_memory_mb?: number;
  };
  errors?: string[];
}

export interface SampleItem {
  id: string;
  title: string;
  description: string;
  recommended_task: TaskType;
  url: string;
  thumbnail: string;
}

export interface SegmentationResult {
  id?: string;
  filename: string;
  task: TaskType;
  tta: boolean;
  dimensions: {
    width: number;
    height: number;
  };
  statistics: {
    total_pixels: number;
    detected_pixels: number;
    coverage_percent: number;
  };
  telemetry: {
    inference_time_ms: number;
    total_time_ms: number;
    device: string;
  };
  images: {
    original: string;
    mask: string;
    overlay: string;
  };
  timestamp?: number;
}

export interface MetricsData {
  task: string;
  weights: string;
  tta: boolean;
  n_test: number;
  metrics: {
    iou: number;
    iou_std?: number;
    dice: number;
    dice_std?: number;
    precision: number;
    precision_std?: number;
    recall: number;
    recall_std?: number;
    accuracy: number;
    accuracy_std?: number;
    relaxed_2px_iou?: number;
    relaxed_2px_iou_std?: number;
    relaxed_2px_precision?: number;
    relaxed_2px_recall?: number;
    relaxed_2px_f1?: number;
    relaxed_3px_iou?: number;
    relaxed_3px_iou_std?: number;
    relaxed_3px_precision?: number;
    relaxed_3px_recall?: number;
    relaxed_3px_f1?: number;
    relaxed_5px_iou?: number;
    relaxed_5px_iou_std?: number;
    relaxed_5px_precision?: number;
    relaxed_5px_recall?: number;
    relaxed_5px_f1?: number;
  };
}
