"use client";

import { useState } from "react";

export function PlannerInput() {
  const [hours, setHours] = useState("");

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-zinc-400 shrink-0">I have</span>
      <input
        type="text"
        value={hours}
        onChange={(e) => setHours(e.target.value)}
        placeholder="3 hours"
        className="w-28 bg-zinc-800 border border-zinc-700 rounded px-2.5 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-500 transition-colors"
      />
      <span className="text-sm text-zinc-400 shrink-0">tonight</span>
      <button
        disabled
        className="ml-2 px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-500 cursor-not-allowed"
        title="AI Planner not yet configured"
      >
        Get Plan →
      </button>
      <span className="text-[10px] text-zinc-700 font-mono">AI Planner coming soon</span>
    </div>
  );
}
