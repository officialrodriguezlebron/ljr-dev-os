interface ProfileBlock {
  label: string;
  items: string[];
}

const PROFILE: ProfileBlock[] = [
  {
    label: "Strong",
    items: [
      "Shopify",
      "Liquid",
      "CRO",
      "TikTok Shop",
      "Customer Service",
      "Claude",
      "ChatGPT",
      "Cursor",
    ],
  },
  {
    label: "Learning",
    items: ["n8n", "AI Agents", "System Design", "GoHighLevel", "Meta Ads"],
  },
  {
    label: "Building",
    items: ["RutaSmart", "CareerOS", "LJR.devOS"],
  },
  {
    label: "Target Roles",
    items: ["Shopify Dev", "AI VA", "SE Intern"],
  },
];

function Tag({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: "neutral" | "green" | "amber" | "blue";
}) {
  const cls = {
    neutral: "bg-zinc-800 text-zinc-400",
    green: "bg-green-500/10 text-green-400 border border-green-500/20",
    amber: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    blue: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  }[variant];
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded font-mono ${cls}`}>
      {children}
    </span>
  );
}

const tagVariant: Record<
  string,
  "neutral" | "green" | "amber" | "blue"
> = {
  Strong: "green",
  Learning: "amber",
  Building: "blue",
  "Target Roles": "neutral",
};

export default function MemoryPage() {
  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center gap-3 mb-1">
        <span className="text-base font-mono text-zinc-500">◑</span>
        <h1 className="text-lg font-semibold text-zinc-50">Memory System</h1>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-wide bg-green-500/10 text-green-400 border border-green-500/20">
          active
        </span>
      </div>
      <p className="text-sm text-zinc-500 mb-6">
        The core of everything. Powers every recommendation across the OS.
      </p>

      {/* Identity card */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-5 mb-4">
        <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-3">
          Identity
        </div>
        <div className="grid grid-cols-2 gap-y-2.5 text-sm">
          <div className="text-zinc-500">Name</div>
          <div className="text-zinc-200 font-medium">Lebron Rodriguez</div>

          <div className="text-zinc-500">School</div>
          <div className="text-zinc-200">FEU-IT · Dean&apos;s List</div>

          <div className="text-zinc-500">Thesis</div>
          <div className="text-zinc-200">
            RutaSmart{" "}
            <span className="text-[10px] text-amber-400 font-mono">
              deadline soon
            </span>
          </div>

          <div className="text-zinc-500">Goal</div>
          <div className="text-zinc-200">Software Engineer</div>
        </div>
      </div>

      {/* Skill blocks */}
      {PROFILE.map(({ label, items }) => (
        <div
          key={label}
          className="bg-zinc-900 rounded-lg border border-zinc-800 p-5 mb-4"
        >
          <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-3">
            {label}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {items.map((item) => (
              <Tag key={item} variant={tagVariant[label] ?? "neutral"}>
                {item}
              </Tag>
            ))}
          </div>
        </div>
      ))}

      {/* Income block */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-5">
        <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-3">
          Income
        </div>
        <div className="grid grid-cols-2 gap-y-2.5 text-sm mb-3">
          <div className="text-zinc-500">Current</div>
          <div className="text-zinc-400 font-mono">₱0 freelance</div>

          <div className="text-zinc-500">Target</div>
          <div className="text-green-400 font-mono">$800 / month</div>
        </div>
        <div className="mt-3 pt-3 border-t border-zinc-800">
          <div className="text-[10px] font-mono text-zinc-600 mb-2">Path</div>
          <div className="flex items-center gap-2 flex-wrap">
            <Tag variant="amber">CareerOS Phase 2</Tag>
            <span className="text-zinc-700 text-xs">→</span>
            <Tag variant="neutral">Land first client</Tag>
            <span className="text-zinc-700 text-xs">→</span>
            <Tag variant="neutral">Income tracking</Tag>
            <span className="text-zinc-700 text-xs">→</span>
            <Tag variant="green">$800/mo</Tag>
          </div>
        </div>
      </div>

      <div className="mt-4 text-[10px] font-mono text-zinc-700">
        AI RUNTIME INTEGRATION PENDING · CURRENTLY STATIC · SUPABASE NEXT
      </div>
    </div>
  );
}
