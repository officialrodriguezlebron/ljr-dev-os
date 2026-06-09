import { ModuleShell } from "../components/ModuleShell";

export default function WorkspacePage() {
  return (
    <ModuleShell
      name="Excel Workspace"
      icon="⊟"
      description="Spreadsheets live inside the OS. n8n updates them automatically — job tracker, weekly planner, sprint board, expenses."
      status="planned"
    />
  );
}
