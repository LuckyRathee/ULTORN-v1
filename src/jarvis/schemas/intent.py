"""
Intent schemas - Discriminated union for type-safe intent routing.

The LLM must return JSON matching one of these models exactly.
Tool-calling / function-calling is used to guarantee valid output.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class IntentType(str, Enum):
    """Supported intent types."""
    WEATHER = "weather"
    CALENDAR_CREATE = "calendar_create"
    CALENDAR_LIST = "calendar_list"
    TASK_CREATE = "task_create"
    TASK_LIST = "task_list"
    UNKNOWN = "unknown"


class WeatherIntent(BaseModel):
    """Get weather for a location."""
    type: Literal[IntentType.WEATHER]
    location: str = Field(..., description="City name or lat,lon coordinates")
    units: Literal["metric", "imperial"] = "metric"
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM confidence score")


class CalendarCreateIntent(BaseModel):
    """Create a calendar event."""
    type: Literal[IntentType.CALENDAR_CREATE]
    title: str = Field(..., min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime
    description: Optional[str] = Field(default=None, max_length=1000)
    confidence: float = Field(..., ge=0.0, le=1.0)


class CalendarListIntent(BaseModel):
    """List calendar events in a date range."""
    type: Literal[IntentType.CALENDAR_LIST]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class TaskCreateIntent(BaseModel):
    """Create a task/todo item."""
    type: Literal[IntentType.TASK_CREATE]
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    due_date: Optional[datetime] = None
    priority: Literal["low", "medium", "high"] = "medium"
    confidence: float = Field(..., ge=0.0, le=1.0)


class TaskListIntent(BaseModel):
    """List tasks with optional status filter."""
    type: Literal[IntentType.TASK_LIST]
    status: Optional[Literal["pending", "completed", "all"]] = "all"
    confidence: float = Field(..., ge=0.0, le=1.0)


class UnknownIntent(BaseModel):
    """Fallback for unrecognized or ambiguous input."""
    type: Literal[IntentType.UNKNOWN]
    raw_text: str = Field(..., description="Original transcript text")
    confidence: float = Field(..., ge=0.0, le=1.0)


# Discriminated union for type-safe routing
# Use: match intent.type: case IntentType.WEATHER: ...
Intent = (
    WeatherIntent
    | CalendarCreateIntent
    | CalendarListIntent
    | TaskCreateIntent
    | TaskListIntent
    | UnknownIntent
)