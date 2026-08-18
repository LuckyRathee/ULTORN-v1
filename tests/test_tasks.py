"""
Tasks Service Integration Tests.

Tests for Notion API integration including error paths.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timezone

from src.jarvis.services.tasks import create_task, list_tasks, TaskError
from src.jarvis.config import settings


class TestTasksService:
    """Test tasks service with mocked HTTP responses."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient."""
        with patch("src.jarvis.services.tasks.httpx.AsyncClient") as mock_client:
            yield mock_client

    @pytest.mark.asyncio
    async def test_create_task_success(self, mock_httpx_client):
        """Test successful task creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "task123",
            "properties": {
                "Title": {"title": [{"text": {"content": "Test Task"}}]},
                "Description": {"rich_text": [{"text": {"content": "Test description"}}]},
                "Due Date": {"date": {"start": "2024-01-20"}},
                "Priority": {"select": {"name": "High"}},
                "Status": {"select": {"name": "Pending"}}
            },
            "created_time": "2024-01-15T10:00:00.000Z"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            due_date = datetime(2024, 1, 20, tzinfo=timezone.utc)
            
            result = await create_task(
                title="Test Task",
                description="Test description",
                due_date=due_date,
                priority="high"
            )
            
            assert result["id"] == "task123"
            assert result["title"] == "Test Task"
            assert result["description"] == "Test description"
            assert result["priority"] == "High"
            assert result["completed"] is False
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_no_api_key(self):
        """Test error when Notion API key not configured."""
        original_api_key = settings.notion_api_key
        settings.notion_api_key = None
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "auth"
            assert "not configured" in str(exc_info.value).lower()
        finally:
            settings.notion_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_create_task_no_database_id(self):
        """Test error when Notion database ID not configured."""
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = None
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "auth"
            assert "not configured" in str(exc_info.value).lower()
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_timeout(self, mock_httpx_client):
        """Test timeout error handling."""
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "timeout"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_401_auth_failure(self, mock_httpx_client):
        """Test 401 authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_403_forbidden(self, mock_httpx_client):
        """Test 403 forbidden error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_429_rate_limit(self, mock_httpx_client):
        """Test 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "rate_limit"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_create_task_500_server_error(self, mock_httpx_client):
        """Test 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await create_task(title="Test")
            
            assert exc_info.value.error_type == "server_error"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_list_tasks_success(self, mock_httpx_client):
        """Test successful task listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "task1",
                    "properties": {
                        "Title": {"title": [{"text": {"content": "Task 1"}}]},
                        "Description": {"rich_text": [{"text": {"content": "First task"}}]},
                        "Due Date": {"date": {"start": "2024-01-20"}},
                        "Priority": {"select": {"name": "High"}},
                        "Status": {"select": {"name": "Pending"}}
                    },
                    "created_time": "2024-01-15T10:00:00.000Z"
                },
                {
                    "id": "task2",
                    "properties": {
                        "Title": {"title": [{"text": {"content": "Task 2"}}]},
                        "Description": {"rich_text": []},
                        "Due Date": {"date": None},
                        "Priority": {"select": {"name": "Medium"}},
                        "Status": {"select": {"name": "Completed"}}
                    },
                    "created_time": "2024-01-14T10:00:00.000Z"
                }
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            result = await list_tasks(status="all")
            
            assert len(result["tasks"]) == 2
            assert result["tasks"][0]["title"] == "Task 1"
            assert result["tasks"][0]["completed"] is False
            assert result["tasks"][1]["title"] == "Task 2"
            assert result["tasks"][1]["completed"] is True
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id

    @pytest.mark.asyncio
    async def test_list_tasks_no_api_key(self):
        """Test error when Notion API key not configured."""
        original_api_key = settings.notion_api_key
        settings.notion_api_key = None
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await list_tasks()
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.notion_api_key = original_api_key

    @pytest.mark.asyncio
    async def test_list_tasks_401_auth_failure(self, mock_httpx_client):
        """Test 401 authentication failure for list."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance
        
        original_api_key = settings.notion_api_key
        original_db_id = settings.notion_database_id
        settings.notion_api_key = "test-api-key"
        settings.notion_database_id = "test-db-id"
        
        try:
            with pytest.raises(TaskError) as exc_info:
                await list_tasks()
            
            assert exc_info.value.error_type == "auth"
        finally:
            settings.notion_api_key = original_api_key
            settings.notion_database_id = original_db_id


class TestTaskError:
    """Test TaskError exception class."""

    def test_task_error_attributes(self):
        """Test TaskError has correct attributes."""
        error = TaskError("Test message", "timeout")
        
        assert error.error_type == "timeout"
        assert error.code == "TASK_ERROR"
        assert error.user_message == "I couldn't access your tasks."
        assert str(error) == "Test message"

    def test_task_error_types(self):
        """Test all valid error types."""
        valid_types = ["timeout", "rate_limit", "server_error", "auth", "bad_params", "not_found", "unknown"]
        
        for error_type in valid_types:
            error = TaskError("Test", error_type)
            assert error.error_type == error_type