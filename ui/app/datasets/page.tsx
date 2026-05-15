"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDatasets, uploadDataset, deleteDataset, syncDatasetsFromLS } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, Trash2, Tag, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { TaskType } from "@/lib/types";

const TASK_LABELS: Record<TaskType, string> = { detect: "Detection", segment: "Segmentation", classify: "Classification" };
const TASK_COLORS: Record<TaskType, string> = { detect: "bg-blue-600", segment: "bg-purple-600", classify: "bg-green-600" };

export default function DatasetsPage() {
  const qc = useQueryClient();
  const { data: datasets = [], isLoading } = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({ name: "", task_type: "detect" as TaskType, class_names: "" });
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const upload = useMutation({
    mutationFn: () => uploadDataset(form.name, form.task_type, form.class_names.split(",").map((c) => c.trim()), files),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["datasets"] }); setFiles([]); setForm({ name: "", task_type: "detect", class_names: "" }); },
  });

  const remove = useMutation({
    mutationFn: deleteDataset,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const sync = useMutation({
    mutationFn: syncDatasetsFromLS,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      if (data.synced === 0) alert("새로 동기화된 프로젝트가 없습니다.");
      else alert(`Label Studio에서 ${data.synced}개 프로젝트를 가져왔습니다.`);
    },
    onError: (e: Error) => alert(`동기화 실패: ${e.message}`),
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    const imgExts = /\.(jpe?g|png|gif|webp|bmp|tiff?)$/i;
    const dropped = Array.from(e.dataTransfer.files).filter(
      (f) => f.type.startsWith("image/") || imgExts.test(f.name)
    );
    if (dropped.length > 0) setFiles((prev) => [...prev, ...dropped]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Datasets</h1>
        <button
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-300 text-sm px-3 py-1.5 rounded transition-colors"
        >
          <RefreshCw size={14} className={sync.isPending ? "animate-spin" : ""} />
          {sync.isPending ? "동기화 중..." : "Label Studio 동기화"}
        </button>
      </div>

      <Card className="bg-gray-900 border-gray-800">
        <CardHeader><CardTitle className="text-sm text-gray-300">새 데이터셋 생성</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <input
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500"
              placeholder="데이터셋 이름"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <select
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
              value={form.task_type}
              onChange={(e) => setForm({ ...form, task_type: e.target.value as TaskType })}
            >
              <option value="detect">Detection</option>
              <option value="segment">Segmentation</option>
              <option value="classify">Classification</option>
            </select>
            <input
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500"
              placeholder="클래스 (쉼표 구분: cat, dog)"
              value={form.class_names}
              onChange={(e) => setForm({ ...form, class_names: e.target.value })}
            />
          </div>

          <div
            onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setDragging(true); }}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragging(true); }}
            onDragLeave={(e) => {
              // relatedTarget이 드롭존 밖일 때만 dragging 해제 (자식 요소 이동 시 false 발생 방지)
              if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
            }}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              dragging ? "border-blue-500 bg-blue-500/10" : "border-gray-700 hover:border-gray-600"
            }`}
          >
            <Upload size={24} className="mx-auto mb-2 text-gray-500" />
            <p className="text-sm text-gray-400">
              {files.length > 0 ? `${files.length}장 선택됨` : "이미지를 드래그하거나 클릭해서 업로드"}
            </p>
            <input ref={fileRef} type="file" multiple accept="image/*" className="hidden"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
          </div>

          <button
            onClick={() => upload.mutate()}
            disabled={!form.name || !form.class_names || files.length === 0 || upload.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
          >
            {upload.isPending ? "업로드 중..." : "데이터셋 생성"}
          </button>
        </CardContent>
      </Card>

      {isLoading ? (
        <p className="text-gray-500 text-sm">로딩 중...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((ds) => (
            <Card key={ds.id} className="bg-gray-900 border-gray-800 hover:border-gray-700 transition-colors">
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div>
                  <CardTitle className="text-sm text-white">{ds.name}</CardTitle>
                  <p className="text-xs text-gray-500 font-mono mt-0.5">{ds.id}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded text-white ${TASK_COLORS[ds.task_type]}`}>
                  {TASK_LABELS[ds.task_type]}
                </span>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span>{ds.image_count}장</span>
                  <span>·</span>
                  <span>{ds.class_names.join(", ")}</span>
                </div>
                <div className="flex gap-2">
                  {ds.ls_project_id && (
                    <Link
                      href={`/labeling/${ds.ls_project_id}`}
                      className="flex-1 flex items-center justify-center gap-1 bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 py-1.5 rounded transition-colors"
                    >
                      <Tag size={12} /> 라벨링
                    </Link>
                  )}
                  <button
                    onClick={() => remove.mutate(ds.id)}
                    className="flex items-center justify-center gap-1 bg-gray-800 hover:bg-red-900 text-xs text-gray-400 hover:text-red-400 px-3 py-1.5 rounded transition-colors"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
