"""
Unit tests for Ultron 2.0 Proactive Daily Briefing Package.
"""

import pytest
from ultron.briefing.models import BriefingConfig, BriefingContent
from ultron.briefing.generator import generate_daily_briefing
from ultron.briefing.scheduler import BriefingScheduler


@pytest.mark.asyncio
async def test_generate_daily_briefing():
    cfg = BriefingConfig(city="Tokyo", include_weather=True)
    briefing = await generate_daily_briefing(cfg)
    
    assert isinstance(briefing, BriefingContent)
    assert briefing.city == "Tokyo"
    assert "Tokyo" in briefing.full_text
    assert briefing.full_text.startswith("Good morning!")


@pytest.mark.asyncio
async def test_briefing_scheduler():
    scheduler = BriefingScheduler()
    scheduler.start()
    assert scheduler._running is True
    scheduler.stop()
    assert scheduler._running is False

