"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

export function AppShell({ title, children }: { title: string; children: React.ReactNode }) {
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    api.listAlerts().then((alerts) => setAlertCount(alerts.length)).catch(() => {});
    const timer = setInterval(() => {
      api.listAlerts().then((alerts) => setAlertCount(alerts.length)).catch(() => {});
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar alertCount={alertCount} />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
          {alertCount > 0 && (
            <span className="text-sm text-red-600">{alertCount} 条未处理告警</span>
          )}
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
