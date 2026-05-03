"use client";
import { useQuery } from "@tanstack/react-query";
import { getDatasets } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { Tag } from "lucide-react";

export default function LabelingListPage() {
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const withProject = datasets.filter((d) => d.ls_project_id);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Labeling</h1>

      {withProject.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-10 text-center text-gray-600 text-sm">
            데이터셋을 먼저 업로드하면 라벨링 프로젝트가 자동 생성됩니다
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {withProject.map((ds) => (
            <Link key={ds.id} href={`/labeling/${ds.ls_project_id}`}>
              <Card className="bg-gray-900 border-gray-800 hover:border-blue-600 transition-colors cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm text-white">{ds.name}</CardTitle>
                  <Tag size={14} className="text-blue-400" />
                </CardHeader>
                <CardContent className="text-xs text-gray-500 space-y-1">
                  <p>{ds.task_type} · {ds.image_count}장</p>
                  <p className="text-gray-600">LS Project #{ds.ls_project_id}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
