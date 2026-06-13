"use client";

import { AppShell } from "@/components/layout/app-shell";
import { RunDetailPanel } from "@/components/tasks/run-detail-panel";
import { api, RunTimeline } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [timeline, setTimeline] = useState<RunTimeline | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!runId) return;
    api
      .getRunTimeline(runId)
      .then((tl) => {
        setTimeline(tl);
        setLogs(tl.events.map((e) => `[${e.source}] ${e.message}`));
      })
      .catch((e) => setError(String(e)));
  }, [runId]);

  return (
    <AppShell title="运行详情">
      <div className="mb-4">
        <Link href="/tasks" className="text-sm text-indigo-600 hover:underline">
          ← 返回任务中心
        </Link>
      </div>
      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
      {!timeline && !error && <p className="text-gray-500">加载中...</p>}
      {timeline && (
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <RunDetailPanel timeline={timeline} logs={logs} taskId={timeline.task_id} />
        </div>
      )}
    </AppShell>
  );
}
