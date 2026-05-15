"use client";
import { useQuery } from "@tanstack/react-query";
import { getLabelingStats } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { ExternalLink, RefreshCw, LogIn } from "lucide-react";
import { useRef, useState } from "react";

const LS_URL = process.env.NEXT_PUBLIC_LABEL_STUDIO_URL ?? "http://localhost:8080";

export default function LabelingPage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeKey, setIframeKey] = useState(0);

  const { data: stats } = useQuery({
    queryKey: ["labeling-stats", projectId],
    queryFn: () => getLabelingStats(projectId),
    refetchInterval: 10000,
  });

  const pct = stats ? Math.round((stats.completed / Math.max(stats.total, 1)) * 100) : 0;

  const handleLoginClick = () => {
    // Open Label Studio login in new tab; after login user can come back and reload iframe
    window.open(`${LS_URL}/user/login/?next=/projects/${projectId}/data`, "_blank");
  };

  const reloadIframe = () => setIframeKey((k) => k + 1);

  return (
    <div className="flex flex-col h-full space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Labeling — Project {projectId}</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={reloadIframe}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded"
          >
            <RefreshCw size={12} /> 새로고침
          </button>
          <a
            href={`${LS_URL}/projects/${projectId}/data`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded"
          >
            <ExternalLink size={12} /> 새 탭에서 열기
          </a>
        </div>
      </div>

      {/* Label Studio 로그인 안내 */}
      <div className="flex items-center justify-between bg-blue-950 border border-blue-800 rounded-lg px-4 py-2.5">
        <div className="text-xs text-blue-300">
          <span className="font-medium">Label Studio 로그인 필요:</span>{" "}
          아래 화면이 로그인 페이지로 표시되면 로그인 후 <strong>새로고침</strong> 버튼을 클릭하세요.
        </div>
        <button
          onClick={handleLoginClick}
          className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded transition-colors whitespace-nowrap ml-4"
        >
          <LogIn size={12} /> Label Studio 로그인
        </button>
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

      <div className="flex-1 rounded-lg overflow-hidden border border-gray-800 bg-gray-900" style={{ minHeight: "calc(100vh - 260px)" }}>
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={`${LS_URL}/projects/${projectId}/data`}
          className="w-full h-full"
          style={{ minHeight: "calc(100vh - 260px)" }}
          title="Label Studio"
        />
      </div>
    </div>
  );
}
