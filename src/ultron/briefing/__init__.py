"""
Ultron 2.0 Proactive Daily Briefing Package.
"""

from .models import BriefingContent, BriefingConfig
from .generator import generate_daily_briefing
from .scheduler import BriefingScheduler

__all__ = [
    "BriefingContent",
    "BriefingConfig",
    "generate_daily_briefing",
    "BriefingScheduler",
]
