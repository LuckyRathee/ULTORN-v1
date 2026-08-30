"""
Tasks Service - Notion API integration for task management.

Uses Notion API with API key authentication.
"""

from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime
import httpx

from ..config import settings
from ..utils.errors import UltronError


@dataclass
class Task:
    """Task data."""
    id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Literal["low", "medium", "high"] = "medium"
    completed: bool = False
    created_at: Optional[datetime] = None


class TaskError(UltronError):
    """Task API error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_params", "not_found", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "TASK_ERROR"
    user_message = "I couldn't access your tasks."


async def create_task(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: Literal["low", "medium", "high"] = "medium",
) -> dict:
    """
    Create a task in Notion.
    
    Args:
        title: Task title
        description: Optional description
        due_date: Optional due date
        priority: Priority level
        
    Returns:
        Dict with created task data
        
    Raises:
        TaskError: With typed error_type
    """
    if not settings.notion_api_key:
        raise TaskError("Notion API key not configured", "auth")
    if not settings.notion_database_id:
        raise TaskError("Notion database ID not configured", "auth")


    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Build properties for Notion database
    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Priority": {"select": {"name": priority.capitalize()}},
        "Status": {"select": {"name": "Pending"}},
    }
    
    if description:
        properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
    
    if due_date:
        properties["Due Date"] = {"date": {"start": due_date.date().isoformat()}}
    
    payload = {
        "parent": {"database_id": settings.notion_database_id},
        "properties": properties,
    }
    
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise TaskError("Notion API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise TaskError(f"Notion API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise TaskError("Notion authentication failed", "auth")
    elif response.status_code == 403:
        raise TaskError("Notion access forbidden - check permissions", "auth")
    elif response.status_code == 429:
        raise TaskError("Notion API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise TaskError(f"Notion API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise TaskError(f"Notion API error: {response.text}", "bad_params")
    
    try:
        data = response.json()
    except Exception as e:
        raise TaskError(f"Invalid JSON response: {e}", "server_error") from e
    
    # Extract task data from Notion response
    props = data.get("properties", {})
    return {
        "id": data.get("id"),
        "title": _extract_title(props.get("Title")),
        "description": _extract_rich_text(props.get("Description")),
        "due_date": _extract_date(props.get("Due Date")),
        "priority": _extract_select(props.get("Priority"), "medium"),
        "completed": _extract_select(props.get("Status"), "Pending") == "Completed",
        "created_at": data.get("created_time"),
    }


async def list_tasks(
    status: Optional[Literal["pending", "completed", "all"]] = "all",
    max_results: int = 20,
) -> dict:
    """
    List tasks from Notion.
    
    Args:
        status: Filter by status
        max_results: Maximum tasks to return
        
    Returns:
        Dict with tasks list
        
    Raises:
        TaskError: With typed error_type
    """
    if not settings.notion_api_key:
        raise TaskError("Notion API key not configured", "auth")
    if not settings.notion_database_id:
        raise TaskError("Notion database ID not configured", "auth")


    
    url = f"https://api.notion.com/v1/databases/{settings.notion_database_id}/query"
    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Build filter
    filter_obj = {}
    if status == "pending":
        filter_obj = {"property": "Status", "select": {"equals": "Pending"}}
    elif status == "completed":
        filter_obj = {"property": "Status", "select": {"equals": "Completed"}}
    
    payload = {
        "page_size": max_results,
        "sorts": [{"property": "Created", "direction": "descending"}],
    }
    
    if filter_obj:
        payload["filter"] = filter_obj
    
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise TaskError("Notion API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise TaskError(f"Notion API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise TaskError("Notion authentication failed", "auth")
    elif response.status_code == 429:
        raise TaskError("Notion API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise TaskError(f"Notion API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise TaskError(f"Notion API error: {response.text}", "bad_params")
    
    try:
        data = response.json()
    except Exception as e:
        raise TaskError(f"Invalid JSON response: {e}", "server_error") from e
    
    tasks = []
    for item in data.get("results", []):
        props = item.get("properties", {})
        tasks.append({
            "id": item.get("id"),
            "title": _extract_title(props.get("Title")),
            "description": _extract_rich_text(props.get("Description")),
            "due_date": _extract_date(props.get("Due Date")),
            "priority": _extract_select(props.get("Priority"), "medium"),
            "completed": _extract_select(props.get("Status"), "Pending") == "Completed",
            "created_at": item.get("created_time"),
        })
    
    return {"tasks": tasks}


async def get_pending_tasks(max_results: int = 20) -> dict:
    """
    Get pending tasks from Notion.
    
    Args:
        max_results: Maximum tasks to return
        
    Returns:
        Dict with tasks list
        
    Raises:
        TaskError: With typed error_type
    """
    return await list_tasks(status="pending", max_results=max_results)


def _extract_title(prop: Optional[dict]) -> str:
    """Extract title from Notion title property."""
    if not prop:
        return "Untitled"
    title_array = prop.get("title", [])
    if not title_array:
        return "Untitled"
    return title_array[0].get("text", {}).get("content", "Untitled")


def _extract_rich_text(prop: Optional[dict]) -> Optional[str]:
    """Extract text from Notion rich_text property."""
    if not prop:
        return None
    text_array = prop.get("rich_text", [])
    if not text_array:
        return None
    return text_array[0].get("text", {}).get("content")


def _extract_date(prop: Optional[dict]) -> Optional[str]:
    """Extract date from Notion date property."""
    if not prop:
        return None
    date_obj = prop.get("date")
    if not date_obj:
        return None
    return date_obj.get("start")


def _extract_select(prop: Optional[dict], default: str) -> str:
    """Extract select value from Notion select property."""
    if not prop:
        return default
    select_obj = prop.get("select")
    if not select_obj:
        return default
    return select_obj.get("name", default)
