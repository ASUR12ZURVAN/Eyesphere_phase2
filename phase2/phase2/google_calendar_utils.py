import datetime
import uuid
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from decouple import config

# Scopes for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Builds and returns a Google Calendar service object."""
    # Try to get credentials from environment variables
    # This assumes a persistent refresh token is available (configured once)
    client_id = config('GOOGLE_CLIENT_ID', default=None)
    client_secret = config('GOOGLE_CLIENT_SECRET', default=None)
    refresh_token = config('GOOGLE_REFRESH_TOKEN', default=None)

    if not all([client_id, client_secret, refresh_token]):
        # No configuration means we can't create an event
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return None

        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Calendar service: {e}")
        return None

def create_meet_event(start_time, summary="Online Eye Consultation", duration_minutes=30):
    """
    Creates a Google Meet event and returns the link.
    start_time: datetime object or ISO string
    """
    service = get_calendar_service()
    if not service:
        return None, "Google Calendar credentials not configured in .env"

    if isinstance(start_time, str):
        # Expecting ISO format '2026-04-02T10:00:00'
        start_dt = datetime.datetime.fromisoformat(start_time)
    else:
        start_dt = start_time

    # Ensure it's offset-aware if needed, but here we'll assume local/UTC
    # For simplicity, we'll treat it as standard
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

    event = {
        'summary': summary,
        'description': 'Online session scheduled via EyeSphere platform.',
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': config('TIME_ZONE', default='UTC'),
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': config('TIME_ZONE', default='UTC'),
        },
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            },
        },
    }

    try:
        event_result = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        meet_link = event_result.get('hangoutLink')
        if not meet_link:
            # Sometimes conference data takes a second or requires a separate check
            # but usually it's in the response if conferenceDataVersion=1
            return None, "Failed to generate Meet link. Check API permissions."

        return meet_link, None
    except Exception as e:
        return None, str(e)
