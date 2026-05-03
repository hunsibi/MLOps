"use client";
import { useQuery } from "@tanstack/react-query";
import { getDatasets, getTrainingJobs, getModels } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, Dumbbell, Box, Tag } from "lucide-react";

export default function Dashboard() {
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: getTrainingJobs, refetchInterval: 5000 });
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: getModels });

  const totalImages = datasets.reduce((s, d) => s + d.image_count, 0);
  const runningJobs = jobs.filter((j) => j.status === "running").length;
  const completedJobs = jobs.filter((j) => j.status === "completed").length;

  const stats = [
    { label: "총 이미지",    value: totalImages,      icon: Database,  color: "text-blue-400" },
    { label: "데이터셋",     value: datasets.length,  icon: Tag,       color: "text-purple-400" },
    { label: "학습 중",      value: runningJobs,       icon: Dumbbell,  color: "text-yellow-400" },
    { label: "등록 모델",    value: models.length,    icon: Box,       color: "text-green-400" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-400">{label}</CardTitle>
              <Icon size={18} className={color} />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">{value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="text-sm text-gray-300">최근 학습 잡</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {jobs.slice(0, 5).map((job) => (
              <div key={job.id} className="flex justify-between items-center text-sm">
                <span className="text-gray-400 font-mono">{job.id}</span>
                <span className="text-gray-500">{job.task_type}</span>
                <StatusBadge status={job.status} />
              </div>
            ))}
            {jobs.length === 0 && <p className="text-gray-600 text-sm">학습 잡 없음</p>}
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="text-sm text-gray-300">파이프라인 상태</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-sm text-gray-400 mt-2">
              {["Upload", "Label", "Train", "Register"].map((step, i, arr) => (
                <div key={step} className="flex items-center gap-2">
                  <div className="flex flex-col items-center gap-1">
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white">
                      {i + 1}
                    </div>
                    <span className="text-xs">{step}</span>
                  </div>
                  {i < arr.length - 1 && <div className="w-8 h-px bg-gray-700" />}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-600 mt-4">완료된 학습: {completedJobs}회</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: "text-yellow-400",
    completed: "text-green-400",
    failed: "text-red-400",
    pending: "text-gray-400",
    cancelled: "text-gray-500",
  };
  return <span className={`text-xs font-medium ${colors[status] ?? "text-gray-400"}`}>{status}</span>;
}
