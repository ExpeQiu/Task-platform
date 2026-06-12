"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const navItems = [
  { href: "/", label: "数据看板 BI" },
  { href: "/tasks", label: "任务中心" },
  { href: "/orchestrator", label: "流程编排" },
];

const adminItems = [
  { href: "/alerts", label: "告警中心" },
  { href: "/audit", label: "治理与审计" },
];

const ecoItems = [
  { href: "/adapters", label: "Agent 接入" },
  { href: "/mcp", label: "MCP 配置" },
];

function NavLink({ href, label, alertCount }: { href: string; label: string; alertCount?: number }) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link
      href={href}
      className={clsx(
        "flex items-center px-4 py-3 rounded-md transition-colors text-sm",
        active ? "bg-gray-800 text-white" : "text-gray-300 hover:bg-gray-800 hover:text-white"
      )}
    >
      {label}
      {alertCount ? (
        <span className="ml-auto bg-red-500 text-white py-0.5 px-2 rounded-full text-xs">{alertCount}</span>
      ) : null}
    </Link>
  );
}

export function Sidebar({ alertCount = 0 }: { alertCount?: number }) {
  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full shadow-lg flex-shrink-0">
      <div className="p-5 flex items-center justify-center border-b border-gray-800">
        <h1 className="text-xl font-bold tracking-wider">Task Platform</h1>
      </div>
      <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink key={item.href} {...item} />
        ))}
        <div className="pt-4 pb-2">
          <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">系统管理</p>
        </div>
        {adminItems.map((item) => (
          <NavLink key={item.href} {...item} alertCount={item.href === "/alerts" ? alertCount : undefined} />
        ))}
        <div className="pt-4 pb-2">
          <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">生态接入</p>
        </div>
        {ecoItems.map((item) => (
          <NavLink key={item.href} {...item} />
        ))}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-sm font-bold">A</div>
          <div className="ml-3">
            <p className="text-sm font-medium">Admin User</p>
            <p className="text-xs text-gray-400">系统管理员</p>
          </div>
        </div>
      </div>
    </div>
  );
}
