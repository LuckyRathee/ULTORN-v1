"""
Calendar Service - Google Calendar API integration.

Uses OAuth2 for authentication. Requires user consent flow.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import httpx

from ..config import settings
from ..utils.errors import JarvisError


@dataclass
class CalendarEvent:
    """Calendar event data."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None


class CalendarError(JarvisError):
    """Calendar API error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_params", "not_found", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "CALENDAR_ERROR"
    user_message = "I couldn't access your calendar."


async def create_calendar_event(
    title: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    """
    Create a calendar event.
    
    Args:
        title: Event title
        start_time: Start datetime (timezone-aware)
        end_time: End datetime (timezone-aware)
        description: Optional description
        access_token: OAuth2 access token (required)
        
    Returns:
        Dict with created event data
        
    Raises:
        CalendarError: With typed error_type
    """
    if not access_token:
        raise CalendarError("Calendar access token required", "auth")
    
    if not settings.google_client_id or not settings.google_client_secret:
        raise CalendarError("Google Calendar not configured", "auth")
    
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "summary": title,
        "start": {"dateTime": start_time.isoformat()},
        "end": {"dateTime": end_time.isoformat()},
    }
    
    if description:
        payload["description"] = description
    
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise CalendarError("Calendar API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise CalendarError(f"Calendar API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise CalendarError("Calendar authentication failed - token may be expired", "auth")
    elif response.status_code == 403:
        raise CalendarError("Calendar access forbidden - check permissions", "auth")
    elif response.status_code == 429:
        raise CalendarError("Calendar API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise CalendarError(f"Calendar API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise CalendarError(f"Calendar API error: {response.text}", "bad_params")
    
    try:
        data = response.json()
    except Exception as e:
        raise CalendarError(f"Invalid JSON response: {e}", "server_error") from e
    
    return {
        "id": data.get("id"),
        "title": data.get("summary"),
        "start_time": data.get("start", {}).get("dateTime"),
        "end_time": data.get("end", {}).get("dateTime"),
        "description": data.get("description"),
    }


async def list_calendar_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    access_token: Optional[str] = None,
    max_results: int = 10,
) -> dict:
    """
    List calendar events in a date range.
    
    Args:
        start_date: Start of range (defaults to now)
        end_date: End of range (defaults to 7 days from now)
        access_token: OAuth2 access token (required)
        max_results: Maximum events to return
        
    Returns:
        Dict with events list
        
    Raises:
        CalendarError: With typed error_type
    """
    if not access_token:
        raise CalendarError("Calendar access token required", "auth")
    
    now = datetime.utcnow()
    time_min = (start_date or now).isoformat() + "Z"
    time_max = (end_date or now.replace(day=now.day + 7)).isoformat() + "Z"
    
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
        except httpx.TimeoutException as e:
            raise CalendarError("Calendar API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise CalendarError(f"Calendar API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise CalendarError("Calendar authentication failed", "auth")
    elif response.status_code == 429:
        raise CalendarError("Calendar API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise CalendarError(f"Calendar API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise CalendarError(f"Calendar API error: {response.text}", "bad_params")
    
    try:
        data = response.json()
    except Exception as e:
        raise CalendarError(f"Invalid JSON response: {e}", "server_error") from e
    
    events = []
    for item in data.get("items", []):
        start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
        end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
        events.append({
            "id": item.get("id"),
            "title": item.get("summary", "Untitled"),
            "start_time": start,
            "end_time": end,
            "description": item.get("description"),
        })
    
    return {"events": events}