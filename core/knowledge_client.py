import logging
import os
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_VA_WORK_PATH = Path(os.getenv("VA_WORK_PATH", r"C:\Users\HomePC\va-work"))
_KNOWLEDGE_PATH = _VA_WORK_PATH / "knowledge"


def _read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def build_knowledge_context() -> str:
    """Return combined knowledge base string for agent system prompts."""
    parts = []

    feedback = _read(_KNOWLEDGE_PATH / "jordan-feedback.md")
    if feedback and "<!--" not in feedback.splitlines()[-1]:
        parts.append(f"## Jordan's Feedback (patterns to apply)\n{feedback}")

    lessons = _read(_KNOWLEDGE_PATH / "lessons-learned.md")
    if lessons and "<!--" not in lessons.splitlines()[-1]:
        parts.append(f"## Lessons Learned\n{lessons}")

    winners_dir = _KNOWLEDGE_PATH / "winners"
    winner_parts = []
    if winners_dir.exists():
        for f in sorted(winners_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8").strip()
            if content:
                winner_parts.append(f"=== {f.stem} ===\n{content}")
    if winner_parts:
        parts.append("## Winning Examples\n" + "\n\n".join(winner_parts))

    return "\n\n".join(parts)


class KnowledgeClient:
    """Read/write the knowledge base for the Phase 7 learning loop."""

    def save_task(self, agent_name: str, request: str, output: str) -> Path:
        today = date.today().isoformat()
        task_dir = _KNOWLEDGE_PATH / "tasks" / f"{today}-{agent_name}"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "request.md").write_text(request, encoding="utf-8")
        (task_dir / "ai-output.md").write_text(output, encoding="utf-8")
        logger.info(f"knowledge_client: task saved → {task_dir.name}")
        return task_dir

    def save_final(self, agent_name: str, final_version: str) -> Path:
        tasks_dir = _KNOWLEDGE_PATH / "tasks"
        if tasks_dir.exists():
            matching = sorted(
                [d for d in tasks_dir.iterdir() if d.is_dir() and agent_name in d.name],
                reverse=True,
            )
            if matching:
                final_path = matching[0] / "final-version.md"
                final_path.write_text(final_version, encoding="utf-8")
                logger.info(f"knowledge_client: final version saved → {final_path}")
                return final_path

        today = date.today().isoformat()
        task_dir = _KNOWLEDGE_PATH / "tasks" / f"{today}-{agent_name}-final"
        task_dir.mkdir(parents=True, exist_ok=True)
        final_path = task_dir / "final-version.md"
        final_path.write_text(final_version, encoding="utf-8")
        return final_path

    def append_lesson(self, lesson: str) -> None:
        path = _KNOWLEDGE_PATH / "lessons-learned.md"
        today = date.today().isoformat()
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n- {today} | {lesson.strip()}")
        logger.info(f"knowledge_client: lesson appended: {lesson[:60]}")

    def append_jordan_feedback(self, feedback: str) -> None:
        path = _KNOWLEDGE_PATH / "jordan-feedback.md"
        today = date.today().isoformat()
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n- {today} | {feedback.strip()}")
        logger.info(f"knowledge_client: Jordan feedback appended: {feedback[:60]}")
