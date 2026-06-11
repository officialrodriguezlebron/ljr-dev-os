import datetime
import logging
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
PHT = datetime.timezone(datetime.timedelta(hours=8))


class CalendarClient:
    def __init__(self) -> None:
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
        self._service = None

    def _connect(self):
        if self._service is None:
            creds = Credentials.from_service_account_file(self.creds_path, scopes=SCOPES)
            self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _check_configured(self) -> None:
        if not self.calendar_id:
            raise ValueError(
                "GOOGLE_CALENDAR_ID not set in .env — "
                "share your calendar with careeros-bot@careeros-498909.iam.gserviceaccount.com "
                "then add GOOGLE_CALENDAR_ID=<your-email-or-calendar-id> to .env"
            )

    def list_events_today(self) -> list[dict]:
        self._check_configured()
        now = datetime.datetime.now(PHT)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return self._list_events(day_start, day_end)

    def list_events_range(self, days: int = 3) -> list[dict]:
        self._check_configured()
        now = datetime.datetime.now(PHT)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = (day_start + datetime.timedelta(days=days - 1)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        return self._list_events(day_start, day_end)

    def _list_events(self, time_min: datetime.datetime, time_max: datetime.datetime) -> list[dict]:
        service = self._connect()
        result = (
            service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
        return result.get("items", [])
