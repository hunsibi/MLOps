"use client";
import { useQuery } from "@tanstack/react-query";
import { getLabelingStats } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { ExternalLink } from "lucide-react";

const LS_URL = process.env.NEXT_PUBLIC_LABEL_STUDIO_URL ?? "http://localhost:8080";

export default function LabelingPage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);

  const { data: stats } = useQuery({
    queryKey: ["labeling-stats", projectId],
    queryFn: () => getLabelingStats(projectId),
    refetchInterval: 10000,
  });

  const pct = stats ? Math.round((stats.completed / Math.max(stats.total, 1)) * 100) : 0;

  return (
    <div className="flex flex-col h-full space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Labeling — Project {projectId}</h1>
        <a
          href={`${LS_URL}/projects/${projectId}/data`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
        >
          <ExternalLink size={12} /> 새 탭에서 열기
        </a>
      </div>

      {stats && (
        <div className="flex items-center gap-4 bg-gray-900 border border-gray-800 rounded-lg px-4 py-2">
          <span className="text-xs text-gray-400">진행률</span>
          <Progress value={pct} className="flex-1 h-2" />
          <span className="text-xs text-gray-300 whitespace-nowrap">
            {stats.completed} / {stats.total} ({pct}%)
          </span>
        </div>
      )}

      <div className="flex-1 rounded-lg overflow-hidden border border-gray-800 bg-gray-900" style={{ minHeight: "calc(100vh - 220px)" }}>
        <iframe
          src={`${LS_URL}/projects/${projectId}/data`}
          className="w-full h-full"
          style={{ minHeight: "calc(100vh - 220px)" }}
          title="Label Studio"
        />
      </div>
    </div>
  );
}
