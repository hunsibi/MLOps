"use client";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html>
      <body style={{ background: "#030712", color: "#f3f4f6", fontFamily: "monospace", padding: "2rem" }}>
        <h2 style={{ color: "#f87171" }}>전역 오류</h2>
        <pre style={{ background: "#111827", padding: "1rem", borderRadius: "8px", overflow: "auto", fontSize: "13px" }}>
          {error.message}
          {error.stack && "\n\n" + error.stack}
        </pre>
        <button
          onClick={reset}
          style={{ marginTop: "1rem", padding: "0.5rem 1rem", background: "#2563eb", color: "white", border: "none", borderRadius: "6px", cursor: "pointer" }}
        >
          다시 시도
        </button>
      </body>
    </html>
  );
}
