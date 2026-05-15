"use client";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 p-8">
      <h2 className="text-xl font-semibold text-red-400">페이지 오류</h2>
      <pre className="text-sm text-gray-300 bg-gray-900 rounded-lg p-4 max-w-2xl overflow-auto whitespace-pre-wrap border border-gray-700">
        {error.message}
        {error.stack && "\n\n" + error.stack}
      </pre>
      <button
        onClick={reset}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
      >
        다시 시도
      </button>
    </div>
  );
}
