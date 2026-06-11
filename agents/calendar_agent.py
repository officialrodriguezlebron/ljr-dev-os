import datetime
import logging

from core.calendar_client import CalendarClient, PHT

logger = logging.getLogger(__name__)

WORK_END_HOUR = 22  # 10pm — stop showing free slots after this


def _fmt_time(event: dict) -> str:
    """Return '9:00 AM' style string from a Calendar event's start field."""
    start = event.get("start", {})
    dt_str = start.get("dateTime", "")
    if dt_str:
        dt = datetime.datetime.fromisoformat(dt_str).astimezone(PHT)
        return dt.strftime("%I:%M %p").lstrip("0")
    return "All day" if start.get("date") else "?"


def _fmt_date(dt: datetime.datetime) -> str:
    """Return 'Wed' style day abbreviation."""
    return dt.strftime("%a")


def _event_start_dt(event: dict) -> datetime.datetime | None:
    start = event.get("start", {})
    dt_str = start.get("dateTime", "")
    if not dt_str:
        return None
    return datetime.datetime.fromisoformat(dt_str).astimezone(PHT)


def _event_end_dt(event: dict) -> datetime.datetime | None:
    end = event.get("end", {})
    dt_str = end.get("dateTime", "")
    if not dt_str:
        return None
    return datetime.datetime.fromisoformat(dt_str).astimezone(PHT)


class CalendarAgent:
    def __init__(self) -> None:
        self.cal = CalendarClient()

    def get_today(self) -> str:
        """
        📅 TODAY — Day, Mon DD
        9:00 AM — Event title
        2:00 PM — Event title
        (or "No events scheduled — open day")
        """
        try:
            events = self.cal.list_events_today()
        except ValueError as e:
            return f"⚠️ Calendar not configured: {e}"
        except Exception as e:
            logger.error(f"calendar get_today failed: {e}")
            return "❌ Could not read calendar. Check GOOGLE_CALENDAR_ID and calendar sharing."

        today = datetime.datetime.now(PHT)
        date_str = today.strftime("%a, %b") + " " + str(today.day)
        lines = [f"📅 TODAY — {date_str}\n"]

        timed = [e for e in events if e.get("start", {}).get("dateTime")]
        allday = [e for e in events if e.get("start", {}).get("date") and not e.get("start", {}).get("dateTime")]

        if allday:
            for e in allday:
                lines.append(f"All day — {e.get('summary', '(no title)')}")

        if timed:
            for e in timed:
                lines.append(f"{_fmt_time(e)} — {e.get('summary', '(no title)')}")
        elif not allday:
            lines.append("No events scheduled — open day")

        return "\n".join(lines).strip()

    def get_free_slots(self) -> str:
        """
        ⏰ FREE TODAY
        11:00 AM – 1:00 PM (2h)
        5:00 PM – 10:00 PM (5h)
        """
        try:
            events = self.cal.list_events_today()
        except ValueError as e:
            return f"⚠️ Calendar not configured: {e}"
        except Exception as e:
            logger.error(f"calendar get_free failed: {e}")
            return "❌ Could not read calendar."

        now = datetime.datetime.now(PHT)
        cursor = now.replace(minute=0, second=0, microsecond=0)
        day_end = now.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)
        if cursor > day_end:
            return "⏰ FREE TODAY\nNo free slots remaining today (past 10pm)."

        timed = sorted(
            [e for e in events if e.get("start", {}).get("dateTime")],
            key=lambda e: _event_start_dt(e) or datetime.datetime.max.replace(tzinfo=PHT),
        )

        slots: list[str] = []
        for event in timed:
            event_start = _event_start_dt(event)
            event_end = _event_end_dt(event)
            if not event_start or not event_end:
                continue
            if event_end <= cursor:
                continue
            gap_start = cursor
            gap_end = event_start
            if gap_end > gap_start:
                minutes = int((gap_end - gap_start).total_seconds() / 60)
                if minutes >= 30:
                    duration = f"{minutes // 60}h" if minutes >= 60 else f"{minutes}m"
                    slots.append(
                        f"{gap_start.strftime('%I:%M %p').lstrip('0')} – "
                        f"{gap_end.strftime('%I:%M %p').lstrip('0')} ({duration})"
                    )
            if event_end > cursor:
                cursor = event_end

        # Slot from cursor to end of day
        if cursor < day_end:
            minutes = int((day_end - cursor).total_seconds() / 60)
            if minutes >= 30:
                duration = f"{minutes // 60}h" if minutes >= 60 else f"{minutes}m"
                slots.append(
                    f"{cursor.strftime('%I:%M %p').lstrip('0')} – "
                    f"{day_end.strftime('%I:%M %p').lstrip('0')} ({duration})"
                )

        if not slots:
            return "⏰ FREE TODAY\nNo free slots ≥30 min today."

        lines = ["⏰ FREE TODAY"]
        lines.extend(slots)
        return "\n".join(lines)

    def get_schedule(self, days: int = 3) -> str:
        """
        📅 Wed: 9:00 AM Class
        📅 Thu: 2:00 PM Interview
        📅 Fri: Open
        """
        try:
            events = self.cal.list_events_range(days=days)
        except ValueError as e:
            return f"⚠️ Calendar not configured: {e}"
        except Exception as e:
            logger.error(f"calendar get_schedule failed: {e}")
            return "❌ Could not read calendar."

        today = datetime.datetime.now(PHT).date()
        days_map: dict[datetime.date, list[str]] = {}
        for i in range(days):
            days_map[today + datetime.timedelta(days=i)] = []

        for event in events:
            start = event.get("start", {})
            dt_str = start.get("dateTime", "")
            date_str = start.get("date", "")
            if dt_str:
                dt = datetime.datetime.fromisoformat(dt_str).astimezone(PHT)
                key = dt.date()
                if key in days_map:
                    days_map[key].append(f"{_fmt_time(event)} {event.get('summary', '(no title)')}")
            elif date_str:
                key = datetime.date.fromisoformat(date_str)
                if key in days_map:
                    days_map[key].append(event.get("summary", "(no title)"))

        lines = []
        for day_date, day_events in sorted(days_map.items()):
            day_label = _fmt_date(datetime.datetime.combine(day_date, datetime.time(), tzinfo=PHT))
            if day_events:
                lines.append(f"📅 {day_label}: " + " · ".join(day_events[:2]))
            else:
                lines.append(f"📅 {day_label}: Open")

        return "\n".join(lines) if lines else "No events in the next 3 days."
