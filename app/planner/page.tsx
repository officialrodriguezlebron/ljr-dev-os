import { ModuleShell } from "../components/ModuleShell";

export default function PlannerPage() {
  return (
    <ModuleShell
      name="AI Planner"
      icon="◎"
      description="You type how much time you have. It reads your projects, deadlines, and skill gaps — then tells you exactly what to do."
      status="planned"
    />
  );
}
