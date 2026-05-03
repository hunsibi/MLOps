"use client";
import { useQuery } from "@tanstack/react-query";

export default function Header() {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: () => fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`).then((r) => r.json()),
    refetchInterval: 30000,
  });

  return (
    <header className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6">
      <span className="text-sm text-gray-400">Image MLOps Pipeline</span>
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span
          className={`w-2 h-2 rounded-full ${data?.status === "ok" ? "bg-green-500" : "bg-red-500"}`}
        />
        API {data?.status === "ok" ? "connected" : "disconnected"}
      </div>
    </header>
  );
}
