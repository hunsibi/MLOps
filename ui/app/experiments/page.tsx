"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getExperiments, getExperimentRuns } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ExperimentsPage() {
  const { data: experiments = [] } = useQuery({ queryKey: ["experiments"], queryFn: getExperiments });
  const [selectedExp, setSelectedExp] = useState<string | null>(null);

  const { data: runs = [] } = useQuery({
    queryKey: ["runs", selectedExp],
    queryFn: () => getExperimentRuns(selectedExp!),
    enabled: !!selectedExp,
  });

  const active = selectedExp ?? experiments[0]?.id;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Experiments</h1>

      {experiments.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-10 text-center text-gray-600 text-sm">
            실험 없음 — 학습 완료 후 자동 기록됩니다
          </CardContent>
        </Card>
      ) : (
        <Tabs value={active} onValueChange={setSelectedExp}>
          <TabsList className="bg-gray-800 border-gray-700">
            {experiments.map((e) => (
              <TabsTrigger key={e.id} value={e.id} className="text-xs data-[state=active]:bg-blue-600">
                {e.name}
              </TabsTrigger>
            ))}
          </TabsList>

          {experiments.map((e) => (
            <TabsContent key={e.id} value={e.id}>
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader><CardTitle className="text-sm text-gray-300">런 목록</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-800 text-xs text-gray-500">
                          <th className="text-left pb-2 pr-4">Run ID</th>
                          <th className="text-left pb-2 pr-4">Status</th>
                          <th className="text-left pb-2 pr-4">mAP50</th>
                          <th className="text-left pb-2 pr-4">box_loss</th>
                          <th className="text-left pb-2">Epochs</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {runs.map((r) => (
                          <tr key={r.run_id} className="hover:bg-gray-800/50 transition-colors">
                            <td className="py-2 pr-4 font-mono text-xs text-gray-400">{r.run_id.slice(0, 8)}...</td>
                            <td className="py-2 pr-4">
                              <span className={`text-xs ${r.status === "FINISHED" ? "text-green-400" : "text-yellow-400"}`}>
                                {r.status}
                              </span>
                            </td>
                            <td className="py-2 pr-4 text-gray-300">{r.metrics["metrics_mAP50"] ?? "—"}</td>
                            <td className="py-2 pr-4 text-gray-300">{r.metrics["train_box_loss"] ?? "—"}</td>
                            <td className="py-2 text-gray-300">{r.params["epochs"] ?? "—"}</td>
                          </tr>
                        ))}
                        {runs.length === 0 && (
                          <tr><td colSpan={5} className="py-6 text-center text-gray-600 text-xs">런 없음</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}
