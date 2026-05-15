"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModels, transitionModelStage } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw } from "lucide-react";
import type { ModelStage } from "@/lib/types";

const STAGE_STYLE: Record<string, string> = {
  Production: "text-green-400 bg-green-400/10 border border-green-400/30",
  Staging:    "text-yellow-400 bg-yellow-400/10 border border-yellow-400/30",
  Archived:   "text-gray-500 bg-gray-500/10 border border-gray-500/30",
  None:       "text-gray-400 bg-gray-400/10 border border-gray-400/20",
};

const TRANSITION_STAGES: ModelStage[] = ["Staging", "Production", "Archived"];

export default function ModelsPage() {
  const qc = useQueryClient();
  const { data: models = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ["models"],
    queryFn: getModels,
    retry: 1,
  });

  const transition = useMutation({
    mutationFn: ({ name, version, stage }: { name: string; version: string; stage: string }) =>
      transitionModelStage(name, version, stage),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Model Registry</h1>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-2 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 disabled:opacity-50 px-3 py-1.5 rounded transition-colors"
        >
          <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
          새로고침
        </button>
      </div>

      {isLoading && (
        <p className="text-gray-400 text-base">모델 목록 로딩 중…</p>
      )}

      {isError && (
        <Card className="bg-red-950 border-red-800">
          <CardContent className="py-6 text-red-300 text-sm flex items-center justify-between">
            <span>모델 목록 조회 실패: {String(error)}</span>
            <button onClick={() => refetch()} className="text-xs underline ml-4 hover:text-red-100">재시도</button>
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && models.length === 0 && (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-12 text-center text-gray-500 text-base">
            등록된 모델 없음 — 학습 완료 후 자동 등록됩니다
          </CardContent>
        </Card>
      )}

      {models.map((model) => (
        <Card key={model.name} className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-white">{model.name}</CardTitle>
            <p className="text-sm text-gray-400">{model.latest_versions.length}개 버전</p>
          </CardHeader>
          <CardContent>
            {model.latest_versions.length === 0 ? (
              <p className="text-sm text-gray-500 py-2">버전 없음</p>
            ) : (
              <div className="space-y-3">
                {model.latest_versions.map((v) => {
                  const stagePending = transition.isPending &&
                    transition.variables?.name === model.name &&
                    transition.variables?.version === v.version;

                  return (
                    <div key={v.version} className="bg-gray-800 rounded-xl px-5 py-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-3">
                            <span className="text-base font-semibold text-white">버전 {v.version}</span>
                            <span className={`text-sm px-2.5 py-0.5 rounded-full font-medium ${STAGE_STYLE[v.stage] ?? STAGE_STYLE.None}`}>
                              {v.stage}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              v.status === "READY" ? "text-blue-400 bg-blue-400/10" : "text-gray-500 bg-gray-700"
                            }`}>
                              {v.status}
                            </span>
                          </div>
                          {v.run_id && (
                            <p className="text-xs text-gray-500 font-mono">
                              run: {v.run_id.slice(0, 16)}…
                            </p>
                          )}
                          {v.description && (
                            <p className="text-sm text-gray-400">{v.description}</p>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-2 shrink-0">
                          {TRANSITION_STAGES.filter((s) => s !== v.stage).map((s) => (
                            <button
                              key={s}
                              disabled={stagePending}
                              onClick={() => transition.mutate({ name: model.name, version: v.version, stage: s })}
                              className="text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 disabled:opacity-40 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              {stagePending ? "…" : `→ ${s}`}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
