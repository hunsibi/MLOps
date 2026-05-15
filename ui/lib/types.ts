export type TaskType = "detect" | "segment" | "classify";
export type JobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type ModelStage = "None" | "Staging" | "Production" | "Archived";

export interface Dataset {
  id: string;
  name: string;
  task_type: TaskType;
  class_names: string[];
  image_count: number;
  ls_project_id: number | null;
  created_at: string;
}

export interface LabelingStats {
  total: number;
  completed: number;
  skipped: number;
}

export interface TrainingJob {
  id: string;
  dataset_id: string;
  task_type: TaskType;
  model_size: string;
  epochs: number;
  status: JobStatus;
  mlflow_run_id: string | null;
  created_at: string;
  updated_at: string;
  error_msg: string | null;
}

export interface TrainingJobCreate {
  dataset_id: string;
  task_type: TaskType;
  model_size: string;
  epochs: number;
  class_names: string[];
}

export interface ModelVersion {
  version: string;
  stage: ModelStage;
  run_id: string | null;
  status: string;
  description: string | null;
}

export interface RegisteredModel {
  name: string;
  latest_versions: ModelVersion[];
}

export interface Experiment {
  id: string;
  name: string;
  artifact_location: string;
  lifecycle_stage: string;
}

export interface Run {
  run_id: string;
  experiment_id: string;
  status: string;
  start_time: number;
  end_time: number | null;
  params: Record<string, string>;
  metrics: Record<string, number>;
  tags: Record<string, string>;
}
