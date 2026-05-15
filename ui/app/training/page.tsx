"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTrainingJobs, createTrainingJob, cancelTrainingJob, getDatasets } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import type { TaskType, TrainingJobCreate } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  running: "text-yellow-400", completed: "text-green-400",
  failed: "text-red-400", pending: "text-gray-400", cancelled: "text-gray-500",
};

export default function TrainingPage() {
  const qc = useQueryClient();
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: getTrainingJobs, refetchInterval: 3000 });
  const {
    data: datasets = [],
    isLoading: datasetsLoading,
    isError: datasetsError,
    refetch: refetchDatasets,
  } = useQuery({ queryKey: ["datasets"], queryFn: getDatasets, retry: 2 });

  const [form, setForm] = useState<TrainingJobCreate>({
    dataset_id: "", task_type: "detect", model_size: "yolo11n", epochs: 100, class_names: [],
  });

  const create = useMutation({
    mutationFn: createTrainingJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const cancel = useMutation({
    mutationFn: cancelTrainingJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const selectedDs = datasets.find((d) => d.id === form.dataset_id);

  const handleDatasetChange = (id: string) => {
    const ds = datasets.find((d) => d.id === id);
    setForm({ ...form, dataset_id: id, task_type: (ds?.task_type ?? "detect") as TaskType, class_names: ds?.class_names ?? [] });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Training</h1>

      <Card className="bg-gray-900 border-gray-800">
        <CardHeader><CardTitle className="text-sm text-gray-300">새 학습 시작</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {datasetsError && (
            <div className="flex items-center justify-between bg-red-900/30 border border-red-700 rounded px-3 py-2 text-sm text-red-300">
              <span>데이터셋 로드 실패</span>
              <button onClick={() => refetchDatasets()} className="text-xs underline hover:text-red-100">재시도</button>
            </div>
          )}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <select
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              value={form.dataset_id}
              onChange={(e) => handleDatasetChange(e.target.value)}
              disabled={datasetsLoading}
            >
              <option value="">
                {datasetsLoading ? "로딩 중..." : datasets.length === 0 ? "데이터셋 없음" : "데이터셋 선택"}
              </option>
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              value={form.task_type}
              onChange={(e) => setForm({ ...form, task_type: e.target.value as TaskType })}
            >
              <option value="detect">Detection</option>
              <option value="segment">Segmentation</option>
              <option value="classify">Classification</option>
            </select>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              value={form.model_size}
              onChange={(e) => setForm({ ...form, model_size: e.target.value })}
            >
              {["yolo11n", "yolo11s", "yolo11m", "yolo11l", "yolo11x"].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <input
              type="number"
              min={1} max={1000}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              value={form.epochs}
              onChange={(e) => setForm({ ...form, epochs: Number(e.target.value) })}
              placeholder="Epochs"
            />
          </div>
          {!datasetsLoading && !datasetsError && datasets.length === 0 && (
            <p className="text-xs text-yellow-500">
              데이터셋이 없습니다.{" "}
              <Link href="/datasets" className="underline hover:text-yellow-300">Datasets 페이지</Link>에서 먼저 업로드하세요.
            </p>
          )}
          {selectedDs && (
            <p className="text-xs text-gray-500">클래스: {selectedDs.class_names.join(", ")} · 이미지: {selectedDs.image_count}장</p>
          )}
          {create.isError && (
            <p className="text-xs text-red-400">학습 시작 실패: {String(create.error)}</p>
          )}
          <button
            onClick={() => create.mutate(form)}
            disabled={!form.dataset_id || !form.class_names.length || create.isPending || datasets.length === 0}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
          >
            {create.isPending ? "시작 중..." : "학습 시작"}
          </button>
        </CardContent>
      </Card>

      <Card className="bg-gray-900 border-gray-800">
        <CardHeader><CardTitle className="text-sm text-gray-300">학습 잡 목록</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {jobs.map((job) => {
              const dsName = datasets.find((d) => d.id === job.dataset_id)?.name ?? job.dataset_id.slice(0, 8);
              return (
              <div key={job.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
                <div className="flex items-center gap-4">
                  <span className="font-mono text-sm text-gray-300">{job.id}</span>
                  <span className="text-xs text-gray-500">{dsName} · {job.task_type} · {job.model_size} · {job.epochs}ep</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-medium ${STATUS_COLOR[job.status]}`}>{job.status}</span>
                  <Link href={`/training/${job.id}`} className="text-xs text-blue-400 hover:text-blue-300">상세</Link>
                  {job.status === "running" && (
                    <button onClick={() => cancel.mutate(job.id)} className="text-xs text-red-400 hover:text-red-300">취소</button>
                  )}
                </div>
              </div>
              );
            })}
            {jobs.length === 0 && <p className="text-gray-600 text-sm text-center py-4">학습 잡 없음</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
