"""
Calendar Service Integration Tests.

Tests for Google Calendar API integration including error paths.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timezone

from src.ultron.services.calendar import create_calendar_event, list_calendar_events, CalendarError
from src.ultron.config import settings


class TestCalendarService:
    """Test calendar service with mocked HTTP responses."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient."""
        with patch("src.ultron.services.calendar.httpx.AsyncClient") as mock_client:
            yield mock_client

    @pytest.mark.asyncio
    async def test_create_calendar_event_success(self, mock_httpx_client):
        """Test successful calendar event creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "event123",
            "summary": "Test Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00+00:00"},
            "end": {"dateTime": "2024-01-15T11:00:00+00:00"},
            "description": "Test description"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            start_time = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)
            
            result = await create_calendar_event(
                title="Test Meeting",
                start_time=start_time,
                end_time=end_time,
                description="Test description",
                access_token="test-access-token"
            )
            
            assert result["id"] == "event123"
            assert result["title"] == "Test Meeting"
            assert result["description"] == "Test description"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_no_access_token(self):
        """Test error when access token not provided."""
        with pytest.raises(CalendarError) as exc_info:
            await create_calendar_event(
                title="Test",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                access_token=None
            )
        
        assert exc_info.value.error_type == "auth"
        assert "required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_calendar_event_not_configured(self):
        """Test error when Google Calendar not configured."""
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = None
        settings.google_client_secret = None
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="test-token"
                )
            
            assert exc_info.value.error_type == "auth"
            assert "not configured" in str(exc_info.value).lower()
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_timeout(self, mock_httpx_client):
        """Test timeout error handling."""
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="test-token"
                )
            
            assert exc_info.value.error_type == "timeout"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_401_auth_failure(self, mock_httpx_client):
        """Test 401 authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="expired-token"
                )
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_403_forbidden(self, mock_httpx_client):
        """Test 403 forbidden error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="test-token"
                )
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_429_rate_limit(self, mock_httpx_client):
        """Test 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="test-token"
                )
            
            assert exc_info.value.error_type == "rate_limit"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_create_calendar_event_500_server_error(self, mock_httpx_client):
        """Test 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_client_id = settings.google_client_id
        original_client_secret = settings.google_client_secret
        settings.google_client_id = "test-client-id"
        settings.google_client_secret = "test-client-secret"
        
        try:
            with pytest.raises(CalendarError) as exc_info:
                await create_calendar_event(
                    title="Test",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    access_token="test-token"
                )
            
            assert exc_info.value.error_type == "server_error"
        finally:
            settings.google_client_id = original_client_id
            settings.google_client_secret = original_client_secret

    @pytest.mark.asyncio
    async def test_list_calendar_events_success(self, mock_httpx_client):
        """Test successful calendar event listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Meeting 1",
                    "start": {"dateTime": "2024-01-15T10:00:00+00:00"},
                    "end": {"dateTime": "2024-01-15T11:00:00+00:00"},
                    "description": "First meeting"
                },
                {
                    "id": "event2",
                    "summary": "Meeting 2",
                    "start": {"dateTime": "2024-01-16T10:00:00+00:00"},
                    "end": {"dateTime": "2024-01-16T11:00:00+00:00"},
                    "description": None
                }
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        result = await list_calendar_events(access_token="test-token")
        
        assert len(result["events"]) == 2
        assert result["events"][0]["title"] == "Meeting 1"
        assert result["events"][1]["title"] == "Meeting 2"

    @pytest.mark.asyncio
    async def test_list_calendar_events_no_access_token(self):
        """Test error when access token not provided."""
        with pytest.raises(CalendarError) as exc_info:
            await list_calendar_events(access_token=None)
        
        assert exc_info.value.error_type == "auth"

    @pytest.mark.asyncio
    async def test_list_calendar_events_401_auth_failure(self, mock_httpx_client):
        """Test 401 authentication failure for list."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        with pytest.raises(CalendarError) as exc_info:
            await list_calendar_events(access_token="expired-token")
        
        assert exc_info.value.error_type == "auth"


class TestCalendarError:
    """Test CalendarError exception class."""

    def test_calendar_error_attributes(self):
        """Test CalendarError has correct attributes."""
        error = CalendarError("Test message", "timeout")
        
        assert error.error_type == "timeout"
        assert error.code == "CALENDAR_ERROR"
        assert error.user_message == "I couldn't access your calendar."
        assert str(error) == "Test message"

    def test_calendar_error_types(self):
        """Test all valid error types."""
        valid_types = ["timeout", "rate_limit", "server_error", "auth", "bad_params", "not_found", "unknown"]
        
        for error_type in valid_types:
            error = CalendarError("Test", error_type)
            assert error.error_type == error_type
