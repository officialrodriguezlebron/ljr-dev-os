import Link from "next/link";
import { PlannerInput } from "./components/PlannerInput";

const STATS = [
  { label: "Active Projects", value: "3", sub: "RutaSmart · CareerOS · LJR.devOS" },
  { label: "Thesis Deadline", value: "~2 wk", sub: "RutaSmart driver dashboard" },
  { label: "Jobs Applied", value: "0", sub: "CareerOS Phase 2 not live yet" },
  { label: "Skills Tracked", value: "12", sub: "8 strong · 4 learning" },
];

const MODULES = [
  {
    name: "Skills Brain",
    href: "/skills",
    icon: "◉",
    desc: "Learns from what you build",
    metric: "12 skills",
    status: "active" as const,
  },
  {
    name: "Project Hub",
    href: "/projects",
    icon: "⬡",
    desc: "Every project in one place",
    metric: "3 active",
    status: "active" as const,
  },
  {
    name: "AI Planner",
    href: "/planner",
    icon: "◎",
    desc: "Tells you exactly what to do next",
    metric: null,
    status: "planned" as const,
  },
  {
    name: "CareerOS",
    href: "/career",
    icon: "◈",
    desc: "Job application engine",
    metric: "0 applied",
    status: "building" as const,
  },
  {
    name: "Workspace",
    href: "/workspace",
    icon: "⊟",
    desc: "Spreadsheets auto-updated by n8n",
    metric: null,
    status: "planned" as const,
  },
  {
    name: "Bridge",
    href: "/bridge",
    icon: "⇌",
    desc: "Sends tasks → Claude Code",
    metric: null,
    status: "planned" as const,
  },
  {
    name: "Memory",
    href: "/memory",
    icon: "◑",
    desc: "Core profile powering everything",
    metric: null,
    status: "active" as const,
  },
];

const statusDot: Record<"active" | "building" | "planned", string> = {
  active: "bg-green-500",
  building: "bg-amber-400",
  planned: "bg-zinc-700",
};

export default function DashboardPage() {
  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-baseline gap-3 mb-1">
          <h1 className="text-xl font-semibold text-zinc-50">
            Hello, Lebron
          </h1>
          <span className="text-xs font-mono text-zinc-600">
            Mon Jun 9, 2026
          </span>
        </div>
        <p className="text-sm text-zinc-500">
          LJR.devOS — Personal Operating System
        </p>
      </div>

      {/* Quick Planner */}
      <div className="mb-8 p-4 bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="text-xs font-mono text-zinc-600 uppercase tracking-widest mb-3">
          What should I do next?
        </div>
        <PlannerInput />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-8 sm:grid-cols-4">
        {STATS.map(({ label, value, sub }) => (
          <div
            key={label}
            className="p-3 bg-zinc-900 rounded-lg border border-zinc-800"
          >
            <div className="text-lg font-semibold text-zinc-50 tabular-nums">
              {value}
            </div>
            <div className="text-[11px] font-medium text-zinc-400 mb-0.5">
              {label}
            </div>
            <div className="text-[10px] text-zinc-600 leading-tight">{sub}</div>
          </div>
        ))}
      </div>

      {/* Modules */}
      <div className="mb-2">
        <div className="text-[10px] font-mono text-zinc-700 uppercase tracking-widest mb-3">
          Modules
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {MODULES.map(({ name, href, icon, desc, metric, status }) => (
            <Link
              key={href}
              href={href}
              className="group p-4 bg-zinc-900 rounded-lg border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/60 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-mono text-zinc-400">{icon}</span>
                <span
                  className={`w-1.5 h-1.5 rounded-full ${statusDot[status]}`}
                />
              </div>
              <div className="text-sm font-medium text-zinc-200 mb-0.5 group-hover:text-zinc-50 transition-colors">
                {name}
              </div>
              <div className="text-[11px] text-zinc-600 leading-tight mb-2">
                {desc}
              </div>
              {metric && (
                <div className="text-[10px] font-mono text-zinc-500">
                  {metric}
                </div>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
