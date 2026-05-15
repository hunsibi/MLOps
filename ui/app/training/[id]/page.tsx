"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTrainingJob, getRun } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STATUS_COLOR: Record<string, string> = {
  running: "text-yellow-400", completed: "text-green-400",
  failed: "text-red-400", pending: "text-gray-400",
};

export default function TrainingDetailPage({ params }: { params: { id: string } }) {
  const jobId = params.id;
  const [logs, setLogs] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getTrainingJob(jobId),
    refetchInterval: (q) => (q.state.data?.status === "running" ? 3000 : false),
  });

  const { data: run } = useQuery({
    queryKey: ["run", job?.mlflow_run_id],
    queryFn: () => getRun(job!.mlflow_run_id!),
    enabled: !!job?.mlflow_run_id,
    refetchInterval: job?.status === "running" ? 5000 : false,
  });

  useEffect(() => {
    if (!job || job.status === "pending") return;
    const es = new EventSource(`${BASE}/api/v1/training/jobs/${jobId}/logs`);
    es.onmessage = (e) => {
      setLogs((prev) => [...prev.slice(-500), e.data]);
      setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 50);
    };
    // Server sends "done" event when job is finished — stop reconnecting
    es.addEventListener("done", () => es.close());
    return () => es.close();
    // "job" intentionally omitted: including the full object causes reconnect on every 3s refetch
  }, [jobId, job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const metricsData = run
    ? Object.entries(run.metrics)
        .filter(([k]) => k.includes("map") || k.includes("loss"))
        .reduce((acc, [k, v]) => {
          acc.push({ name: k, value: Number(v.toFixed(4)) });
          return acc;
        }, [] as { name: string; value: number }[])
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold text-white">Training Job</h1>
        <span className="font-mono text-sm text-gray-400">{jobId}</span>
        {job && <span className={`text-sm font-medium ${STATUS_COLOR[job.status]}`}>{job.status}</span>}
      </div>

      {job && (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              {[
                ["Task", job.task_type],
                ["Model", job.model_size],
                ["Epochs", job.epochs],
                ["Dataset", job.dataset_id],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-500">{k}</p>
                  <p className="text-white font-medium">{v}</p>
                </div>
              ))}
            </div>
            {job.error_msg && <p className="mt-3 text-xs text-red-400 bg-red-900/20 rounded p-2">{job.error_msg}</p>}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {run && metricsData.length > 0 && (
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader><CardTitle className="text-sm text-gray-300">메트릭</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {metricsData.map(({ name, value }) => (
                  <div key={name} className="flex justify-between text-sm">
                    <span className="text-gray-400">{name}</span>
                    <span className="text-white font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader><CardTitle className="text-sm text-gray-300">로그</CardTitle></CardHeader>
          <CardContent>
            <div
              ref={logRef}
              className="bg-black rounded p-3 h-64 overflow-y-auto font-mono text-xs text-green-400 space-y-0.5"
            >
              {logs.length === 0
                ? <span className="text-gray-600">로그 대기 중...</span>
                : logs.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
