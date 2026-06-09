import { ModuleShell } from "../components/ModuleShell";

export default function BridgePage() {
  return (
    <ModuleShell
      name="Claude Code Bridge"
      icon="⇌"
      description="Create a task in Project Hub → click Send to Claude Code → Claude receives the context and builds autonomously."
      status="planned"
    />
  );
}
