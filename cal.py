import os

import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pytz

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def generate_event(start, end, summary, description, location):
    utc = pytz.timezone("UTC")
    utc_start = start.astimezone(utc)
    utc_end = end.astimezone(utc)
    return {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": utc_start.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": utc_end.isoformat(),
            "timeZone": "UTC",
        },
        "recurrence": [],
        "attendees": [],
        "reminders": {
            "useDefault": False,
            "overrides": [],
        },
    }


def get_calendar_id(service, calendar_name):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list["items"]:
            if calendar_list_entry["summary"] == calendar_name:
                return calendar_list_entry["id"]
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            break
    return None


def get_all_events(service, calendar_id):
    ret_events = []
    page_token = None
    while True:
        events = (
            service.events()
            .list(
                calendarId=calendar_id,
                pageToken=page_token,
                orderBy="startTime",
                singleEvents=True,
            )
            .execute()
        )
        ret_events = ret_events + events.get("items", [])
        page_token = events.get("nextPageToken")
        if not page_token:
            break
    return ret_events


def authenticate():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)
