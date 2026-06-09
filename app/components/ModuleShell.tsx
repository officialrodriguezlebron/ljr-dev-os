type Status = "active" | "building" | "planned";

const statusStyle: Record<Status, string> = {
  active: "bg-green-500/10 text-green-400 border border-green-500/20",
  building: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  planned: "bg-zinc-800 text-zinc-500 border border-zinc-700",
};

interface ModuleShellProps {
  name: string;
  icon: string;
  description: string;
  status?: Status;
  note?: string;
}

export function ModuleShell({
  name,
  icon,
  description,
  status = "planned",
  note,
}: ModuleShellProps) {
  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-xl">{icon}</span>
        <h1 className="text-lg font-semibold text-zinc-50">{name}</h1>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-wide ${statusStyle[status]}`}
        >
          {status}
        </span>
      </div>
      <p className="text-sm text-zinc-400 mb-8">{description}</p>

      <div className="rounded-lg border border-dashed border-zinc-800 p-8 text-center">
        <p className="text-xs text-zinc-600 font-mono">
          {note ?? "Module queued — builds after CareerOS Phase 2"}
        </p>
      </div>
    </div>
  );
}
