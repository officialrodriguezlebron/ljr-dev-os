import base64
import datetime
import logging
import os

import httpx

logger = logging.getLogger(__name__)

_TOGGL_BASE = "https://api.track.toggl.com/api/v9"
_WEEKLY_TARGET_HOURS = 20

# Jordan's exact category names for the "Lazy Sun" Toggl project
# Use these as the first word(s) of any /toggl entry description
# e.g. "/toggl PDPs: Hoodie-Acorn copy 45min"
LAZYSUN_CATEGORIES = [
    "PDPs",
    "Photo Editing",
    "Meta Ads",
    "TikTok Shop",
    "Content/Social",
    "Email",
    "Admin",
]


def _infer_category(description: str) -> str | None:
    """Match the start of a description to a known LazySun category."""
    desc_lower = description.lower().strip()
    for cat in LAZYSUN_CATEGORIES:
        if desc_lower.startswith(cat.lower()):
            return cat
    return None


def _auth_header(api_token: str) -> dict:
    token = base64.b64encode(f"{api_token}:api_token".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


async def _get_workspace_id(api_token: str) -> int | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_TOGGL_BASE}/workspaces", headers=_auth_header(api_token))
        resp.raise_for_status()
        workspaces = resp.json()
        if workspaces:
            return workspaces[0]["id"]
    return None


async def _get_time_entries(api_token: str, start_date: str, end_date: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_TOGGL_BASE}/me/time_entries",
            headers=_auth_header(api_token),
            params={"start_date": start_date, "end_date": end_date},
        )
        resp.raise_for_status()
        return resp.json() or []


class TogglAgent:

    def _get_token(self) -> str:
        return os.getenv("TOGGL_API_TOKEN", "")

    def _get_project_id(self) -> int | None:
        pid = os.getenv("TOGGL_LAZYSUN_PROJECT_ID", "")
        return int(pid) if pid.isdigit() else None

    async def log_time(self, description: str, duration_min: int = 30) -> str:
        api_token = self._get_token()
        if not api_token:
            return "❌ Toggl not configured — add TOGGL_API_TOKEN to .env"

        project_id = self._get_project_id()
        workspace_id_env = os.getenv("TOGGL_WORKSPACE_ID", "")

        try:
            if workspace_id_env.isdigit():
                workspace_id = int(workspace_id_env)
            else:
                workspace_id = await _get_workspace_id(api_token)
            if not workspace_id:
                return "❌ Could not determine Toggl workspace ID"

            now = datetime.datetime.utcnow()
            start = now - datetime.timedelta(minutes=duration_min)
            start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")

            category = _infer_category(description)
            body: dict = {
                "description": description,
                "start": start_iso,
                "duration": duration_min * 60,
                "workspace_id": workspace_id,
                "created_with": "ljr-devos",
                "tags": [category] if category else [],
            }
            if project_id:
                body["project_id"] = project_id

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{_TOGGL_BASE}/workspaces/{workspace_id}/time_entries",
                    headers=_auth_header(api_token),
                    json=body,
                )
                resp.raise_for_status()
                entry = resp.json()

            cat_label = f" [{category}]" if category else " [Uncategorized — prefix with PDPs/Photo Editing/etc.]"
            return (
                f"✅ Toggl logged: *{description}*\n"
                f"Duration: {duration_min}min | Project: {'Lazy Sun' if project_id else 'default'}{cat_label}"
            )

        except httpx.HTTPStatusError as e:
            return f"❌ Toggl API error {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            return f"❌ Toggl error: {e}"

    async def get_hours(self) -> str:
        api_token = self._get_token()
        if not api_token:
            return "❌ Toggl not configured — add TOGGL_API_TOKEN to .env"

        today = datetime.date.today()
        # Week starts Monday
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)

        try:
            entries = await _get_time_entries(
                api_token,
                week_start.isoformat(),
                (week_end + datetime.timedelta(days=1)).isoformat(),
            )
        except Exception as e:
            return f"❌ Toggl fetch error: {e}"

        project_id = self._get_project_id()

        # Filter to LazySun project if configured
        if project_id:
            entries = [e for e in entries if e.get("project_id") == project_id]

        # Aggregate by day
        day_totals: dict[str, int] = {}
        total_sec = 0
        for entry in entries:
            dur = entry.get("duration", 0)
            if dur <= 0:
                continue  # Running timer
            start_str = entry.get("start", "")
            try:
                day = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00")).strftime("%a %b %d")
            except Exception:
                day = "Unknown"
            day_totals[day] = day_totals.get(day, 0) + dur
            total_sec += dur

        total_hrs = total_sec / 3600
        target_hrs = _WEEKLY_TARGET_HOURS
        days_elapsed = max(1, today.weekday() + 1)
        days_in_week = 5
        expected_hrs = target_hrs * (days_elapsed / days_in_week)
        pace = "ahead" if total_hrs >= expected_hrs else "behind"
        gap = abs(total_hrs - expected_hrs)

        lines = [f"*Toggl — Week of {week_start.strftime('%b %d')}*\n"]
        for day, sec in sorted(day_totals.items()):
            lines.append(f"{day}: {sec / 3600:.1f}hrs")

        lines.append(f"\n*Total: {total_hrs:.1f}hrs / {target_hrs}hrs target*")
        lines.append(f"Pace: {pace} by {gap:.1f}hrs")

        if total_hrs < target_hrs:
            remaining = target_hrs - total_hrs
            days_left = max(1, days_in_week - days_elapsed)
            lines.append(f"Remaining: {remaining:.1f}hrs over {days_left} days = {remaining / days_left:.1f}hrs/day")

        return "\n".join(lines)

    async def get_report(self) -> str:
        api_token = self._get_token()
        if not api_token:
            return "❌ Toggl not configured — add TOGGL_API_TOKEN to .env"

        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)

        try:
            entries = await _get_time_entries(
                api_token,
                week_start.isoformat(),
                (week_end + datetime.timedelta(days=1)).isoformat(),
            )
        except Exception as e:
            return f"❌ Toggl fetch error: {e}"

        project_id = self._get_project_id()
        if project_id:
            entries = [e for e in entries if e.get("project_id") == project_id]

        # Group by LazySun category (from tags), fallback to description-inferred category
        cat_totals: dict[str, int] = {cat: 0 for cat in LAZYSUN_CATEGORIES}
        untracked_sec = 0
        total_sec = 0
        for entry in entries:
            dur = entry.get("duration", 0)
            if dur <= 0:
                continue
            total_sec += dur
            tags = entry.get("tags") or []
            matched = next((t for t in tags if t in LAZYSUN_CATEGORIES), None)
            if not matched:
                desc = entry.get("description", "").strip()
                matched = _infer_category(desc)
            if matched:
                cat_totals[matched] = cat_totals.get(matched, 0) + dur
            else:
                untracked_sec += dur

        total_hrs = total_sec / 3600
        lines = [
            f"*LazySun — Weekly Report*",
            f"*Week: {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}*",
            f"*Total: {total_hrs:.1f} / {_WEEKLY_TARGET_HOURS}hrs*\n",
            "*Hours by category:*",
        ]
        for cat in LAZYSUN_CATEGORIES:
            sec = cat_totals.get(cat, 0)
            if sec > 0:
                lines.append(f"• {cat}: {sec / 3600:.1f}hrs")
        if untracked_sec > 0:
            lines.append(f"• Uncategorized: {untracked_sec / 3600:.1f}hrs _(prefix entries with category name to track)_")

        lines.append("\n_Paste into Friday report → add Completed / Blockers / Next week plan_")
        lines.append("_Generated by LJR.devOS_")
        return "\n".join(lines)
