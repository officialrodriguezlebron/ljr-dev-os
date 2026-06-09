"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { label: "Dashboard", href: "/", icon: "⊹" },
  { label: "Skills Brain", href: "/skills", icon: "◉", meta: "12 skills" },
  { label: "Project Hub", href: "/projects", icon: "⬡", meta: "3 active" },
  { label: "AI Planner", href: "/planner", icon: "◎" },
  { label: "CareerOS", href: "/career", icon: "◈", meta: "Phase 2" },
  { label: "Workspace", href: "/workspace", icon: "⊟" },
  { label: "Bridge", href: "/bridge", icon: "⇌" },
  { label: "Memory", href: "/memory", icon: "◑" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-52 shrink-0 bg-zinc-900 border-r border-zinc-800">
      <div className="px-4 py-4 border-b border-zinc-800">
        <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-0.5">
          System v0.1
        </div>
        <div className="text-sm font-semibold text-zinc-50 tracking-tight">
          LJR.devOS
        </div>
      </div>

      <nav className="flex-1 py-2 overflow-y-auto">
        {NAV.map(({ label, href, icon, meta }) => {
          const active =
            href === "/"
              ? pathname === "/"
              : pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-2.5 px-3 py-2 text-sm transition-colors ${
                active
                  ? "text-zinc-50 bg-zinc-800"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60"
              }`}
            >
              <span className="w-4 text-center text-xs leading-none font-mono">
                {icon}
              </span>
              <span className="flex-1 text-xs">{label}</span>
              {meta && (
                <span className="text-[10px] text-zinc-600 tabular-nums">
                  {meta}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-[10px] font-bold text-black shrink-0">
            LR
          </div>
          <div className="min-w-0">
            <div className="text-xs font-medium text-zinc-300 truncate">
              Lebron Rodriguez
            </div>
            <div className="text-[10px] text-zinc-600">FEU-IT · Dean&apos;s List</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
