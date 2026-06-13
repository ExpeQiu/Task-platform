"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

export function AppShell({ title, children }: { title: string; children: React.ReactNode }) {
  const [alertCount, setAlertCount] = useState(0);
  const [approvalCount, setApprovalCount] = useState(0);

  const refreshCounts = () => {
    api.listAlerts().then((alerts) => setAlertCount(alerts.length)).catch(() => {});
    api.listPendingApprovals().then((a) => setApprovalCount(a.length)).catch(() => {});
  };

  useEffect(() => {
    refreshCounts();
    const timer = setInterval(refreshCounts, 15000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar alertCount={alertCount} approvalCount={approvalCount} />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
          <div className="flex gap-4 text-sm">
            {approvalCount > 0 && (
              <span className="text-rose-600">{approvalCount} 条待审批</span>
            )}
            {alertCount > 0 && (
              <span className="text-red-600">{alertCount} 条未处理告警</span>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
