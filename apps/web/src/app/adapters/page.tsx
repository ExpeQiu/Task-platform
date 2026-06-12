"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, Adapter } from "@/lib/api";
import { useEffect, useState } from "react";

export default function AdaptersPage() {
  const [adapters, setAdapters] = useState<Adapter[]>([]);

  useEffect(() => {
    api.listAdapters().then(setAdapters).catch(console.error);
  }, []);

  const toggleOnline = async (adapter: Adapter) => {
    await api.updateAdapter(adapter.id, { is_online: !adapter.is_online });
    api.listAdapters().then(setAdapters);
  };

  return (
    <AppShell title="Agent 接入">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adapters.map((adapter) => (
          <div key={adapter.id} className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold">{adapter.name}</h3>
              <span className={`px-2 py-1 text-xs rounded-full ${adapter.is_online ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>
                {adapter.is_online ? "Online" : "Offline"}
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-2">{adapter.adapter_type}</p>
            <p className="text-sm text-gray-600 mb-4">{adapter.description}</p>
            <div className="text-xs text-gray-500 space-y-1">
              <p>协议: {adapter.protocol === "push" ? "Webhook (Push)" : "Polling (Pull)"}</p>
              <p className="truncate">Endpoint: {adapter.endpoint}</p>
            </div>
            <button
              onClick={() => toggleOnline(adapter)}
              className="mt-4 text-sm text-indigo-600 hover:text-indigo-900"
            >
              {adapter.is_online ? "停用" : "启用"}
            </button>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
