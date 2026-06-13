import datetime
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BRAIN_PATH = Path(os.getenv("BRAIN_PATH", r"C:\Users\HomePC\ljr-brain"))
_BASE_SCHEDULE_PATH = _BRAIN_PATH / "wiki" / "concepts" / "base-schedule.md"

_FLEX_LABELS = [
    ("lazysun", "LazySun — VA work"),
    ("rutasmart", "RutaSmart — compliance items"),
    ("ljrdevos", "LJR.devOS / brain"),
]

_OPEN_DAYS = {"Friday", "Saturday", "Sunday"}


def _parse_time(s: str) -> Optional[datetime.time]:
    import re
    m = re.match(r"(\d{1,2}):(\d{2})", s.strip())
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return datetime.time(h, mn)
    return None


def _fmt(t: datetime.time) -> str:
    return t.strftime("%H:%M")


def _add_min(t: datetime.time, minutes: int) -> datetime.time:
    dt = datetime.datetime.combine(datetime.date.today(), t) + datetime.timedelta(minutes=minutes)
    return dt.time()


def _gap_min(start: datetime.time, end: datetime.time) -> int:
    return max(0, (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute))


class ScheduleEngine:

    def _load_fixed_blocks(self, day_name: str) -> list[dict]:
        if not _BASE_SCHEDULE_PATH.exists():
            logger.warning(f"schedule_engine: base-schedule.md not found at {_BASE_SCHEDULE_PATH}")
            return []

        blocks = []
        for line in _BASE_SCHEDULE_PATH.read_text(encoding="utf-8").splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 7:
                continue
            if parts[1].lower() != day_name.lower():
                continue
            time_str = parts[2]
            sep = "–" if "–" in time_str else ("-" if "-" in time_str else None)
            if sep is None:
                continue
            halves = time_str.split(sep)
            if len(halves) != 2:
                continue
            start = _parse_time(halves[0])
            end = _parse_time(halves[1])
            if start is None or end is None:
                continue
            blocks.append({
                "start": start,
                "end": end,
                "course": parts[4],
                "room": parts[5],
                "type": parts[6] if len(parts) > 6 else "on-campus",
            })

        return sorted(blocks, key=lambda b: b["start"])

    def get_today_schedule(self) -> str:
        today = datetime.date.today()
        day_name = today.strftime("%A")
        date_str = today.strftime("%A, %B %d, %Y")

        fixed = self._load_fixed_blocks(day_name)
        is_open = day_name in _OPEN_DAYS

        initial = {"lazysun": 300 if is_open else 210, "rutasmart": 90, "ljrdevos": 90}
        remaining = dict(initial)
        plan_blocks: list[tuple[datetime.time, datetime.time, str]] = []

        day_start = datetime.time(8, 0)
        day_end = datetime.time(22, 0)
        buffer_min = 60
        effective_end = _add_min(day_end, -buffer_min)

        def fill_gap(gap_start: datetime.time, gap_end: datetime.time) -> None:
            avail = _gap_min(gap_start, gap_end)
            if avail < 30:
                return
            pos = gap_start
            for key, label in _FLEX_LABELS:
                if avail <= 0:
                    break
                if remaining[key] <= 0:
                    continue
                give = min(remaining[key], avail)
                plan_blocks.append((pos, _add_min(pos, give), label))
                remaining[key] -= give
                avail -= give
                pos = _add_min(pos, give)

        # Build busy list with commute buffers for on-campus blocks
        busy: list[tuple[datetime.time, datetime.time]] = []
        for b in fixed:
            if "on-campus" in b.get("type", ""):
                buf = _add_min(b["start"], -30)
                if buf < day_start:
                    buf = day_start
                busy.append((buf, b["start"]))
            busy.append((b["start"], b["end"]))
        busy.sort()

        cursor = day_start
        for b_start, b_end in busy:
            if cursor < b_start:
                cap = b_start if b_start < effective_end else effective_end
                fill_gap(cursor, cap)
            if b_end > cursor:
                cursor = b_end

        if cursor < effective_end:
            fill_gap(cursor, effective_end)

        # Format output
        lines = [f"📅 {date_str}\n"]

        lines.append("*FIXED:*")
        if fixed:
            for b in fixed:
                lines.append(f"{_fmt(b['start'])}–{_fmt(b['end'])}: {b['course']} ({b['room']}) [FIXED]")
        else:
            lines.append("No classes today")

        lines.append("")
        lines.append("*PLAN:*")
        for start, end, label in plan_blocks:
            lines.append(f"{_fmt(start)}–{_fmt(end)}: {label}")

        # Show unscheduled time before the buffer as "Free / rest"
        if plan_blocks and plan_blocks[-1][1] < effective_end:
            lines.append(f"{_fmt(plan_blocks[-1][1])}–{_fmt(effective_end)}: Free / rest")
        elif not plan_blocks:
            lines.append(f"{_fmt(day_start)}–{_fmt(effective_end)}: Free / rest")

        lines.append(f"{_fmt(effective_end)}–{_fmt(day_end)}: Buffer / rest")

        lazysun_h = (initial["lazysun"] - remaining["lazysun"]) / 60
        rutasmart_h = (initial["rutasmart"] - remaining["rutasmart"]) / 60
        ljrdevos_h = (initial["ljrdevos"] - remaining["ljrdevos"]) / 60
        lines.append(
            f"\nTOTAL: LazySun {lazysun_h:.1f}hrs | "
            f"RutaSmart {rutasmart_h:.1f}hrs | "
            f"LJR.devOS {ljrdevos_h:.1f}hrs"
        )

        return "\n".join(lines)

    async def adjust_schedule(self, adjustment: str, ai) -> str:
        base = self.get_today_schedule()
        today = datetime.date.today()
        now = datetime.datetime.now().strftime("%H:%M")

        prompt = f"""Today is {today.strftime('%A, %B %d, %Y')}. Current time: {now}.

Current day plan:
{base}

Adjustment requested: "{adjustment}"

Rules:
- FIXED blocks (school classes) are immovable under any circumstances
- Only modify flexible blocks (LazySun, RutaSmart, LJR.devOS, Buffer)
- Do not touch blocks that have already started/passed (before {now})
- If the adjustment conflicts with a FIXED block, say so clearly and leave the FIXED block alone
- Maintain flex priority: LazySun > RutaSmart > LJR.devOS
- If time is removed: cut lower-priority blocks first, preserve higher-priority ones

Output ONLY this exact format, no explanation or preamble:
⚡ ADJUSTED — {today.strftime('%A, %B %d')}

Adjustment: [one-line summary of what changed]

REMAINDER OF TODAY:
HH:MM–HH:MM: [block label] [FIXED if a school class]
...

[If something was deferred]: Moved to tomorrow: [what]"""

        return await ai.chat(
            "You are a schedule recomputer. Output only the adjusted schedule in the exact format specified. No explanation.",
            prompt,
            max_tokens=400,
        )
