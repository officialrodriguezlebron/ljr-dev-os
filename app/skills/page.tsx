type Level = "advanced" | "intermediate" | "beginner" | "learning";

interface Skill {
  name: string;
  level: Level;
  sources: string[];
  note?: string;
}

const STRONG: Skill[] = [
  { name: "Shopify", level: "advanced", sources: ["LuxeWear", "Client work"] },
  { name: "Liquid", level: "advanced", sources: ["LuxeWear"] },
  { name: "CRO", level: "intermediate", sources: ["LuxeWear"] },
  { name: "Claude", level: "intermediate", sources: ["CareerOS", "LJR.devOS"] },
  { name: "ChatGPT", level: "intermediate", sources: ["CareerOS"] },
  { name: "Cursor", level: "intermediate", sources: ["CareerOS", "RutaSmart"] },
  { name: "TikTok Shop", level: "intermediate", sources: ["LuxeWear"] },
  { name: "Customer Service", level: "intermediate", sources: ["Client work"] },
];

const LEARNING: Skill[] = [
  {
    name: "n8n",
    level: "beginner",
    sources: ["LJR.devOS"],
    note: "73% of target roles",
  },
  {
    name: "AI Agents",
    level: "learning",
    sources: ["LJR.devOS"],
    note: "core for OS automation",
  },
  {
    name: "System Design",
    level: "learning",
    sources: [],
    note: "SE Intern requirement",
  },
  {
    name: "GoHighLevel",
    level: "learning",
    sources: [],
    note: "client work opportunity",
  },
  {
    name: "Meta Ads",
    level: "learning",
    sources: [],
    note: "client work opportunity",
  },
];

const LEVEL_META: Record<
  Level,
  { filled: number; label: string; color: string }
> = {
  advanced: { filled: 4, label: "Advanced", color: "text-green-400" },
  intermediate: { filled: 3, label: "Intermediate", color: "text-green-400" },
  beginner: { filled: 2, label: "Beginner", color: "text-amber-400" },
  learning: { filled: 1, label: "Learning", color: "text-amber-400" },
};

function Dots({ level }: { level: Level }) {
  const { filled, color } = LEVEL_META[level];
  return (
    <span className="flex gap-0.5 items-center">
      {Array.from({ length: 4 }, (_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            i < filled ? color.replace("text-", "bg-") : "bg-zinc-800"
          }`}
        />
      ))}
    </span>
  );
}

function SkillRow({ skill }: { skill: Skill }) {
  const { label, color } = LEVEL_META[skill.level];
  return (
    <div className="flex items-center gap-4 py-2.5 border-b border-zinc-800/60 last:border-0">
      <div className="w-36 text-sm text-zinc-200 font-medium">{skill.name}</div>
      <div className="flex items-center gap-2 w-32">
        <Dots level={skill.level} />
        <span className={`text-[11px] font-mono ${color}`}>{label}</span>
      </div>
      <div className="flex gap-1.5 flex-1">
        {skill.sources.map((src) => (
          <span
            key={src}
            className="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-500 rounded font-mono"
          >
            {src}
          </span>
        ))}
      </div>
      {skill.note && (
        <div className="text-[10px] text-zinc-600 font-mono shrink-0">
          → {skill.note}
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  count,
  skills,
}: {
  title: string;
  count: number;
  skills: Skill[];
}) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest">
          {title}
        </span>
        <span className="text-[10px] font-mono text-zinc-700">({count})</span>
      </div>
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 px-4">
        {skills.map((skill) => (
          <SkillRow key={skill.name} skill={skill} />
        ))}
      </div>
    </div>
  );
}

export default function SkillsPage() {
  const total = STRONG.length + LEARNING.length;

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-1">
        <span className="text-base font-mono text-zinc-500">◉</span>
        <h1 className="text-lg font-semibold text-zinc-50">Skills Brain</h1>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-wide bg-green-500/10 text-green-400 border border-green-500/20">
          active
        </span>
      </div>
      <p className="text-sm text-zinc-500 mb-6">
        Learns from what you build. Never manual input.
      </p>

      <div className="flex items-center gap-6 mb-8 p-4 bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="text-center">
          <div className="text-2xl font-semibold text-zinc-50 tabular-nums">
            {total}
          </div>
          <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-wide">
            Total
          </div>
        </div>
        <div className="w-px h-8 bg-zinc-800" />
        <div className="text-center">
          <div className="text-2xl font-semibold text-green-400 tabular-nums">
            {STRONG.length}
          </div>
          <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-wide">
            Strong
          </div>
        </div>
        <div className="w-px h-8 bg-zinc-800" />
        <div className="text-center">
          <div className="text-2xl font-semibold text-amber-400 tabular-nums">
            {LEARNING.length}
          </div>
          <div className="text-[10px] text-zinc-600 font-mono uppercase tracking-wide">
            Learning
          </div>
        </div>
        <div className="flex-1" />
        <div className="text-[10px] font-mono text-zinc-700">
          AUTO-UPDATED · STATIC FOR NOW · SUPABASE PENDING
        </div>
      </div>

      <Section title="Strong" count={STRONG.length} skills={STRONG} />
      <Section title="Learning" count={LEARNING.length} skills={LEARNING} />
    </div>
  );
}
