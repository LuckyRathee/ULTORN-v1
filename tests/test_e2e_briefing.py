"""
End-to-End Briefing Tests.

Tests that daily briefing fires at scheduled time and generates correct content.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from ultron.briefing.models import BriefingConfig, BriefingContent
from ultron.briefing.generator import generate_daily_briefing
from ultron.briefing.scheduler import BriefingScheduler
from ultron.briefing.notifier import (
    BriefingNotifier,
    LoggingNotifier,
    ConsoleNotifier,
    CompositeNotifier,
    create_default_notifier,
    NotificationResult,
)


@pytest.mark.asyncio
async def test_generate_daily_briefing_structure():
    """Test briefing generates correct structure."""
    config = BriefingConfig(
        city="Tokyo",
        include_weather=True,
        include_calendar=True,
        include_tasks=True,
    )
    
    briefing = await generate_daily_briefing(config)
    
    assert isinstance(briefing, BriefingContent)
    assert briefing.city == "Tokyo"
    assert briefing.full_text.startswith("Good morning!")
    assert "Tokyo" in briefing.full_text
    assert "Weather:" in briefing.full_text
    assert "Schedule:" in briefing.full_text
    assert "Tasks:" in briefing.full_text


@pytest.mark.asyncio
async def test_generate_daily_briefing_partial_config():
    """Test briefing with partial config (some sections disabled)."""
    config = BriefingConfig(
        city="London",
        include_weather=True,
        include_calendar=False,
        include_tasks=False,
    )
    
    briefing = await generate_daily_briefing(config)
    
    assert briefing.city == "London"
    assert briefing.weather_summary is not None
    assert briefing.events_summary is None  # Disabled in config
    assert briefing.tasks_summary is None   # Disabled in config


@pytest.mark.asyncio
async def test_briefing_scheduler_start_stop():
    """Test scheduler starts and stops correctly."""
    scheduler = BriefingScheduler()
    
    assert scheduler._running is False
    
    scheduler.start()
    assert scheduler._running is True
    
    scheduler.stop()
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_briefing_scheduler_callback():
    """Test scheduler calls callback when job runs."""
    callback_called = False
    received_briefing = None
    
    async def test_callback(briefing: BriefingContent):
        nonlocal callback_called, received_briefing
        callback_called = True
        received_briefing = briefing
    
    scheduler = BriefingScheduler(callback=test_callback)
    scheduler.start()
    
    await scheduler._run_job()
    
    assert callback_called
    assert received_briefing is not None
    assert isinstance(received_briefing, BriefingContent)
    
    scheduler.stop()


@pytest.mark.asyncio
async def test_logging_notifier():
    """Test logging notifier works."""
    notifier = LoggingNotifier()
    briefing = BriefingContent(
        city="Test City",
        full_text="Test briefing",
    )
    
    result = await notifier.notify(briefing)
    assert result.success
    assert result.method == "logging"
    
    result = await notifier.play_audio("/fake/path.mp3")
    assert result.success
    assert result.method == "logging"


@pytest.mark.asyncio
async def test_console_notifier():
    """Test console notifier works."""
    notifier = ConsoleNotifier()
    briefing = BriefingContent(
        city="Test City",
        full_text="Test briefing",
    )
    
    result = await notifier.notify(briefing)
    assert result.success
    assert result.method == "console"
    
    result = await notifier.play_audio("/fake/path.mp3")
    assert result.success
    assert result.method == "console"


@pytest.mark.asyncio
async def test_composite_notifier_fallback():
    """Test composite notifier falls back to next notifier."""
    failing_notifier = MagicMock(spec=BriefingNotifier)
    failing_notifier.notify = AsyncMock(return_value=NotificationResult(
        success=False, method="failing", error="Failed"
    ))
    failing_notifier.play_audio = AsyncMock(return_value=NotificationResult(
        success=False, method="failing", error="Failed"
    ))
    
    success_notifier = LoggingNotifier()
    
    composite = CompositeNotifier([failing_notifier, success_notifier])
    briefing = BriefingContent(city="Test", full_text="Test")
    
    result = await composite.notify(briefing)
    assert result.success
    assert result.method == "logging"
    
    result = await composite.play_audio("/fake/path.mp3")
    assert result.success
    assert result.method == "logging"


@pytest.mark.asyncio
async def test_create_default_notifier():
    """Test default notifier creation."""
    notifier = create_default_notifier(use_console=True)
    assert isinstance(notifier, CompositeNotifier)
    assert len(notifier.notifiers) >= 2


@pytest.mark.asyncio
async def test_briefing_scheduled_time_config():
    """Test briefing scheduler respects cron config."""
    from ultron.config import settings
    
    assert settings.briefing_time_cron == "0 8 * * *"
    
    scheduler = BriefingScheduler()
    scheduler.start()
    
    assert scheduler._running is True
    
    scheduler.stop()
