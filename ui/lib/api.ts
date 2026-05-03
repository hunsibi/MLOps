import type {
  Dataset, TrainingJob, TrainingJobCreate,
  RegisteredModel, ModelVersion, Experiment, Run, LabelingStats
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

// Datasets
export const getDatasets = () => request<Dataset[]>("/api/v1/datasets/");
export const getDataset = (id: string) => request<Dataset>(`/api/v1/datasets/${id}`);
export const deleteDataset = (id: string) =>
  request<{ deleted: string }>(`/api/v1/datasets/${id}`, { method: "DELETE" });

export async function uploadDataset(
  name: string, taskType: string, classNames: string[], files: File[]
): Promise<Dataset> {
  const form = new FormData();
  form.append("name", name);
  form.append("task_type", taskType);
  form.append("class_names", classNames.join(","));
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE}/api/v1/datasets/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
  return res.json();
}

// Labeling
export const getLabelingProjects = () => request<any[]>("/api/v1/labeling/projects");
export const getLabelingStats = (id: number) =>
  request<LabelingStats>(`/api/v1/labeling/projects/${id}/stats`);

// Training
export const getTrainingJobs = () => request<TrainingJob[]>("/api/v1/training/jobs");
export const getTrainingJob = (id: string) => request<TrainingJob>(`/api/v1/training/jobs/${id}`);
export const createTrainingJob = (body: TrainingJobCreate) =>
  request<TrainingJob>("/api/v1/training/jobs", { method: "POST", body: JSON.stringify(body) });
export const cancelTrainingJob = (id: string) =>
  request<{ cancelled: string }>(`/api/v1/training/jobs/${id}`, { method: "DELETE" });

// Models
export const getModels = () => request<RegisteredModel[]>("/api/v1/models/");
export const getModelVersions = (name: string) =>
  request<ModelVersion[]>(`/api/v1/models/${name}/versions`);
export const transitionModelStage = (name: string, version: string, stage: string) =>
  request(`/api/v1/models/${name}/stage`, {
    method: "POST",
    body: JSON.stringify({ version, stage }),
  });

// Experiments
export const getExperiments = () => request<Experiment[]>("/api/v1/experiments/");
export const getExperimentRuns = (id: string) =>
  request<Run[]>(`/api/v1/experiments/${id}/runs`);
export const getRun = (runId: string) => request<Run>(`/api/v1/experiments/runs/${runId}`);
