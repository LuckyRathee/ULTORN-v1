"""
Pydantic schemas for Daily Proactive Briefing.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BriefingConfig(BaseModel):
    """Configuration for Daily Briefing generation."""
    city: str = "San Francisco"
    include_weather: bool = True
    include_calendar: bool = True
    include_tasks: bool = True


class BriefingContent(BaseModel):
    """Generated briefing response content."""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    city: str
    weather_summary: Optional[str] = None
    events_summary: Optional[str] = None
    tasks_summary: Optional[str] = None
    full_text: str
    audio_url: Optional[str] = None
