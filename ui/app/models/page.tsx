"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModels, transitionModelStage } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ModelStage } from "@/lib/types";

const STAGE_COLOR: Record<ModelStage, string> = {
  Production: "text-green-400 bg-green-400/10",
  Staging: "text-yellow-400 bg-yellow-400/10",
  Archived: "text-gray-500 bg-gray-500/10",
  None: "text-gray-600 bg-gray-600/10",
};

export default function ModelsPage() {
  const qc = useQueryClient();
  const { data: models = [], isLoading } = useQuery({ queryKey: ["models"], queryFn: getModels });

  const transition = useMutation({
    mutationFn: ({ name, version, stage }: { name: string; version: string; stage: string }) =>
      transitionModelStage(name, version, stage),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Model Registry</h1>

      {isLoading ? (
        <p className="text-gray-500 text-sm">로딩 중...</p>
      ) : models.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-10 text-center text-gray-600 text-sm">
            등록된 모델 없음 — 학습 완료 후 자동 등록됩니다
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {models.map((model) => (
            <Card key={model.name} className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="text-base text-white">{model.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {model.latest_versions.map((v) => (
                    <div key={v.version} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-300">v{v.version}</span>
                        <span className="text-xs text-gray-500 font-mono">{v.run_id.slice(0, 8)}...</span>
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${STAGE_COLOR[v.stage as ModelStage] ?? STAGE_COLOR.None}`}>
                          {v.stage}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {(["Staging", "Production", "Archived"] as ModelStage[])
                          .filter((s) => s !== v.stage)
                          .map((s) => (
                            <button
                              key={s}
                              onClick={() => transition.mutate({ name: model.name, version: v.version, stage: s })}
                              className="text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded transition-colors"
                            >
                              → {s}
                            </button>
                          ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
