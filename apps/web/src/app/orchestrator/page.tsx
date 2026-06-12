"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useEffect, useState } from "react";

const DEFAULT_DAG = {
  nodes: [
    { id: "start", type: "Start", label: "接收 Webhook" },
    { id: "openclaw", type: "Agent Task", label: "OpenClaw 抓取" },
    { id: "hermes", type: "Agent Task", label: "Hermes 总结" },
    { id: "end", type: "End", label: "输出报告并告警" },
  ],
};

export default function OrchestratorPage() {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const draft = localStorage.getItem("orchestrator_draft");
    if (!draft) localStorage.setItem("orchestrator_draft", JSON.stringify(DEFAULT_DAG));
  }, []);

  const saveDraft = () => {
    localStorage.setItem("orchestrator_draft", JSON.stringify(DEFAULT_DAG));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <AppShell title="流程编排">
      <div className="h-full flex flex-col bg-white border border-gray-200 rounded-lg shadow-sm min-h-[500px]">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-gray-50">
          <h3 className="text-lg font-medium">流程设计器 (DAG) — UI 占位</h3>
          <div className="space-x-2">
            <button onClick={saveDraft} className="bg-white border border-gray-300 text-gray-700 px-3 py-1.5 rounded-md text-sm hover:bg-gray-50">
              保存草稿
            </button>
            <button className="bg-indigo-600 text-white px-3 py-1.5 rounded-md text-sm opacity-50 cursor-not-allowed" title="Phase 2">
              发布流程
            </button>
          </div>
        </div>
        {saved && <div className="px-6 py-2 bg-green-50 text-green-700 text-sm">草稿已保存到 localStorage</div>}
        <div className="flex-1 bg-gray-100 p-8 flex items-center justify-center">
          <div className="relative flex flex-col items-center space-y-6">
            <div className="bg-white border-2 border-indigo-500 rounded-lg p-4 shadow-md w-48 text-center">
              <div className="text-xs text-gray-500 mb-1">Start Node</div>
              <div className="font-bold">接收 Webhook</div>
            </div>
            <div className="w-0.5 h-6 bg-gray-400" />
            <div className="flex space-x-8">
              <div className="bg-white border border-gray-300 rounded-lg p-4 shadow-md w-48 text-center">
                <div className="text-xs text-blue-500 mb-1">Agent Task</div>
                <div className="font-bold">OpenClaw 抓取</div>
              </div>
              <div className="bg-white border border-gray-300 rounded-lg p-4 shadow-md w-48 text-center">
                <div className="text-xs text-purple-500 mb-1">Agent Task</div>
                <div className="font-bold">Hermes 总结</div>
              </div>
            </div>
            <div className="w-0.5 h-6 bg-gray-400" />
            <div className="bg-white border border-gray-300 rounded-lg p-4 shadow-md w-48 text-center">
              <div className="text-xs text-green-500 mb-1">End Node</div>
              <div className="font-bold">输出报告并告警</div>
            </div>
          </div>
        </div>
        <p className="px-6 py-3 text-sm text-gray-500 border-t">MVP 阶段：流程编排为 UI 占位，执行引擎将在 Phase 2 实现。</p>
      </div>
    </AppShell>
  );
}
