"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getExperiments, getExperimentRuns } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Run } from "@/lib/types";

function formatTime(ms: number | null) {
  if (!ms) return "—";
  return new Date(ms).toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" });
}

function formatDuration(start: number, end: number | null) {
  if (!end) return "—";
  const s = Math.round((end - start) / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

function MetricBadge({ label, value }: { label: string; value: number | undefined }) {
  if (value === undefined) return null;
  return (
    <div className="flex flex-col items-center bg-gray-800 rounded-lg px-4 py-2 min-w-[80px]">
      <span className="text-xs text-gray-400 truncate">{label}</span>
      <span className="text-base font-semibold text-white">{typeof value === "number" ? value.toFixed(4) : value}</span>
    </div>
  );
}

function RunRow({ run }: { run: Run }) {
  const [open, setOpen] = useState(false);

  const mAP50 = run.metrics["metrics_mAP50B"] ?? run.metrics["metrics/mAP50B"] ?? run.metrics["metrics_mAP50"];
  const mAP   = run.metrics["metrics_mAP50-95B"] ?? run.metrics["metrics/mAP50-95B"] ?? run.metrics["metrics_mAP50-95"];
  const boxLoss = run.metrics["train_box_loss"] ?? run.metrics["train/box_loss"];

  return (
    <>
      <tr
        className="border-b border-gray-800 hover:bg-gray-800/60 transition-colors cursor-pointer"
        onClick={() => setOpen((o) => !o)}
      >
        <td className="py-3 pr-4 font-mono text-sm text-blue-400">{run.run_id.slice(0, 8)}…</td>
        <td className="py-3 pr-4">
          <span className={`text-sm font-medium px-2 py-0.5 rounded ${
            run.status === "FINISHED" ? "text-green-400 bg-green-400/10" : "text-yellow-400 bg-yellow-400/10"
          }`}>
            {run.status}
          </span>
        </td>
        <td className="py-3 pr-4 text-sm text-white">{mAP50 !== undefined ? mAP50.toFixed(4) : "—"}</td>
        <td className="py-3 pr-4 text-sm text-white">{mAP !== undefined ? mAP.toFixed(4) : "—"}</td>
        <td className="py-3 pr-4 text-sm text-white">{boxLoss !== undefined ? boxLoss.toFixed(4) : "—"}</td>
        <td className="py-3 pr-4 text-sm text-gray-300">{run.params["epochs"] ?? "—"}</td>
        <td className="py-3 text-sm text-gray-400">{formatTime(run.start_time)}</td>
        <td className="py-3 text-sm text-gray-400">{formatDuration(run.start_time, run.end_time)}</td>
      </tr>
      {open && (
        <tr className="bg-gray-900/80">
          <td colSpan={8} className="px-4 pb-4 pt-2">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-2">Parameters</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(run.params).map(([k, v]) => (
                    <span key={k} className="text-xs bg-gray-800 text-gray-300 px-2 py-1 rounded">
                      <span className="text-gray-500">{k}:</span> {v}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-2">All Metrics</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(run.metrics).map(([k, v]) => (
                    <MetricBadge key={k} label={k} value={v} />
                  ))}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ExperimentsPage() {
  const { data: experiments = [], isLoading, isError } = useQuery({
    queryKey: ["experiments"],
    queryFn: getExperiments,
  });

  const [selectedExpId, setSelectedExpId] = useState<string | null>(null);
  const activeId = selectedExpId ?? experiments[0]?.id ?? null;

  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ["runs", activeId],
    queryFn: () => getExperimentRuns(activeId!),
    enabled: !!activeId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Experiments</h1>
        <p className="text-gray-400 text-sm">로딩 중…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Experiments</h1>
        <Card className="bg-red-950 border-red-800">
          <CardContent className="py-8 text-center text-red-300 text-sm">
            MLflow에 연결할 수 없습니다. 서비스가 실행 중인지 확인하세요.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Experiments</h1>

      {experiments.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-12 text-center text-gray-500 text-base">
            실험 없음 — 학습 완료 후 자동 기록됩니다
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Experiment selector */}
          <div className="flex gap-2 flex-wrap">
            {experiments.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelectedExpId(e.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  e.id === activeId
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white"
                }`}
              >
                {e.name}
                <span className="ml-2 text-xs opacity-60">#{e.id}</span>
              </button>
            ))}
          </div>

          {/* Runs table */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-base text-white">
                런 목록
                {runs.length > 0 && (
                  <span className="ml-2 text-sm text-gray-400 font-normal">({runs.length}개)</span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runsLoading ? (
                <p className="text-gray-400 text-sm py-4">런 로딩 중…</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-700 text-left">
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">Run ID</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">Status</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">mAP50</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">mAP50-95</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">box_loss</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">Epochs</th>
                        <th className="pb-3 pr-4 text-sm font-medium text-gray-400">시작 시간</th>
                        <th className="pb-3 text-sm font-medium text-gray-400">소요 시간</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.map((r) => (
                        <RunRow key={r.run_id} run={r} />
                      ))}
                      {runs.length === 0 && (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-gray-500 text-sm">
                            이 실험에 런이 없습니다
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
