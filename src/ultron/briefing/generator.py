"""
Briefing Generator: Aggregates Weather, Calendar, and Tasks into a natural spoken briefing.
"""

import asyncio
from typing import Optional

from .models import BriefingConfig, BriefingContent
from .tts_cache import get_tts_cache
from ..config import settings
from ..services.weather import get_weather, get_default_location
from ..services.calendar import get_today_events
from ..services.tasks import get_pending_tasks
from ..services.tts import synthesize_speech
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def generate_daily_briefing(
    config: Optional[BriefingConfig] = None,
    calendar_access_token: Optional[str] = None,
) -> BriefingContent:
    """
    Generate a complete proactive daily briefing.
    
    Aggregates weather, calendar schedule, and pending tasks.
    Synthesizes a friendly morning update text and generates TTS audio with caching.
    """
    cfg = config or BriefingConfig(city=settings.default_city)
    
    weather_summary = None
    events_summary = None
    tasks_summary = None

    # Fetch weather
    if cfg.include_weather:
        try:
            if settings.weather_api_key:
                wdata = await get_weather(cfg.city)
                loc = wdata.get("location", cfg.city)
                temp = wdata.get("temperature", 20)
                cond = wdata.get("condition", "Clear")
                temp_val = int(round(temp)) if isinstance(temp, (int, float)) else temp
                weather_summary = f"{cond} and {temp_val} degrees Celsius in {loc}"
            else:
                weather_summary = f"a pleasant 22 degrees Celsius and sunny in {cfg.city}"
        except Exception as e:
            logger.warning("briefing_weather_fetch_failed", error=str(e))
            weather_summary = f"clear skies in {cfg.city}"

    # Fetch calendar events
    if cfg.include_calendar:
        try:
            if calendar_access_token and settings.google_client_id:
                events_data = await get_today_events(access_token=calendar_access_token)
                events = events_data.get("events", [])
                if events:
                    event_lines = []
                    for event in events[:5]:  # Limit to 5 events
                        title = event.get("title", "Untitled")
                        start = event.get("start_time", "")
                        if start:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                                time_str = dt.strftime("%I:%M %p").lstrip("0")
                            except Exception:
                                time_str = start
                        else:
                            time_str = "unknown time"
                        event_lines.append(f"{title} at {time_str}")
                    
                    if len(events) > 5:
                        event_lines.append(f"... and {len(events) - 5} more")
                    
                    events_summary = "; ".join(event_lines)
                else:
                    events_summary = "no events scheduled today"
            else:
                events_summary = "calendar not connected"
        except Exception as e:
            logger.warning("briefing_calendar_fetch_failed", error=str(e))
            events_summary = "unable to fetch calendar"

    # Fetch tasks
    if cfg.include_tasks:
        try:
            if settings.notion_api_key and settings.notion_database_id:
                tasks_data = await get_pending_tasks(max_results=10)
                tasks = tasks_data.get("tasks", [])
                if tasks:
                    task_lines = []
                    for task in tasks[:5]:  # Limit to 5 tasks
                        title = task.get("title", "Untitled")
                        priority = task.get("priority", "medium")
                        priority_marker = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                        task_lines.append(f"{priority_marker} {title}")
                    
                    if len(tasks) > 5:
                        task_lines.append(f"... and {len(tasks) - 5} more")
                    
                    tasks_summary = "; ".join(task_lines)
                else:
                    tasks_summary = "no pending tasks"
            else:
                tasks_summary = "tasks not connected"
        except Exception as e:
            logger.warning("briefing_tasks_fetch_failed", error=str(e))
            tasks_summary = "unable to fetch tasks"

    # Assemble full synthesized briefing text
    full_text = (
        f"Good morning! Here is your daily briefing for {cfg.city}.\n"
        f"Weather: Currently {weather_summary}.\n"
        f"Schedule: You have {events_summary}.\n"
        f"Tasks: {tasks_summary}.\n"
        f"Have a productive day!"
    )

    audio_url = None
    if settings.tts_provider != "none":
        try:
            # Check cache first
            cache = get_tts_cache()
            cached_path = cache.get(
                text=full_text,
                provider=settings.tts_provider,
                voice_id=settings.elevenlabs_voice_id,
            )
            
            if cached_path:
                audio_url = cached_path
                logger.info("briefing_tts_cache_hit")
            else:
                audio_url = await synthesize_speech(
                    text=full_text,
                    provider=settings.tts_provider,
                    voice_id=settings.elevenlabs_voice_id,
                )
                # Store in cache
                if audio_url:
                    cache.put(
                        text=full_text,
                        provider=settings.tts_provider,
                        audio_path=audio_url,
                        voice_id=settings.elevenlabs_voice_id,
                    )
        except Exception as e:
            logger.error("briefing_tts_failed", error=str(e))

    return BriefingContent(
        city=cfg.city,
        weather_summary=weather_summary,
        events_summary=events_summary,
        tasks_summary=tasks_summary,
        full_text=full_text,
        audio_url=audio_url,
    )
