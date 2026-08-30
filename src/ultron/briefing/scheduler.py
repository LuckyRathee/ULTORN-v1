"""
Background scheduler for Proactive Daily Briefings using APScheduler with asyncio fallback.
"""

import asyncio
from typing import Optional, Callable
from ..config import settings
from .generator import generate_daily_briefing
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BriefingScheduler:
    """Schedules daily proactive briefings."""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self._scheduler = None
        self._task = None
        self._running = False

    def start(self):
        """Start the briefing scheduler."""
        if not settings.briefing_enabled:
            logger.info("briefing_scheduler_disabled_by_config")
            return

        if self._running:
            return

        self._running = True

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger

            self._scheduler = AsyncIOScheduler()
            trigger = CronTrigger.from_crontab(settings.briefing_time_cron)
            self._scheduler.add_job(self._run_job, trigger=trigger, id="daily_briefing")
            self._scheduler.start()
            logger.info("apscheduler_started", cron=settings.briefing_time_cron)
        except Exception as e:
            logger.info("apscheduler_unavailable_using_loop_fallback", reason=str(e))
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._fallback_loop())
            except RuntimeError:
                logger.info("no_running_loop_deferring_fallback_scheduler")


    async def _run_job(self):
        logger.info("executing_scheduled_daily_briefing")
        try:
            briefing = await generate_daily_briefing()
            if self.callback:
                await self.callback(briefing)
        except Exception as e:
            logger.error("daily_briefing_job_failed", error=str(e))

    async def _fallback_loop(self):
        """Fallback background loop when APScheduler is not installed."""
        while self._running:
            await asyncio.sleep(3600)  # Check hourly

    def stop(self):
        """Stop the briefing scheduler."""
        self._running = False
        if self._scheduler:
            try:
                self._scheduler.shutdown()
            except Exception:
                pass
            self._scheduler = None
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("briefing_scheduler_stopped")
