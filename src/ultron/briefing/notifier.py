"""
Briefing Notifier - Abstract base and Tauri implementation.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from .models import BriefingContent
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    method: str
    error: Optional[str] = None


class BriefingNotifier(ABC):
    """Abstract base class for briefing notification delivery."""

    @abstractmethod
    async def notify(self, briefing: BriefingContent) -> NotificationResult:
        """
        Deliver a briefing notification to the user.
        
        Args:
            briefing: The generated briefing content
            
        Returns:
            NotificationResult indicating success/failure
        """
        pass

    @abstractmethod
    async def play_audio(self, audio_path: str) -> NotificationResult:
        """
        Play an audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            NotificationResult indicating success/failure
        """
        pass


class LoggingNotifier(BriefingNotifier):
    """Fallback notifier that just logs the briefing."""

    async def notify(self, briefing: BriefingContent) -> NotificationResult:
        logger.info(
            "briefing_notification_logged",
            city=briefing.city,
            text_preview=briefing.full_text[:100],
        )
        return NotificationResult(success=True, method="logging")

    async def play_audio(self, audio_path: str) -> NotificationResult:
        logger.info("audio_playback_logged", path=audio_path)
        return NotificationResult(success=True, method="logging")


class ConsoleNotifier(BriefingNotifier):
    """Notifier that prints to console (for development/debugging)."""

    async def notify(self, briefing: BriefingContent) -> NotificationResult:
        print("\n" + "=" * 50)
        print("📅 DAILY BRIEFING")
        print("=" * 50)
        print(briefing.full_text)
        print("=" * 50 + "\n")
        return NotificationResult(success=True, method="console")

    async def play_audio(self, audio_path: str) -> NotificationResult:
        print(f"🔊 Playing audio: {audio_path}")
        return NotificationResult(success=True, method="console")


class TauriNotifier(BriefingNotifier):
    """
    Tauri-specific notifier that uses system notifications and audio playback.
    
    Requires Tauri frontend to be running and listening for commands.
    """

    def __init__(
        self,
        send_command: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
    ):
        """
        Initialize Tauri notifier.
        
        Args:
            send_command: Async function to send commands to Tauri frontend.
                         Signature: send_command(command: str, payload: dict) -> dict
        """
        self._send_command = send_command
        self._fallback = LoggingNotifier()

    async def notify(self, briefing: BriefingContent) -> NotificationResult:
        if self._send_command:
            try:
                result = await self._send_command("show_notification", {
                    "title": f"Daily Briefing - {briefing.city}",
                    "body": briefing.full_text[:200] + ("..." if len(briefing.full_text) > 200 else ""),
                    "audio_url": briefing.audio_url,
                })
                if result.get("success"):
                    return NotificationResult(success=True, method="tauri_notification")
            except Exception as e:
                logger.warning("tauri_notification_failed", error=str(e))
        
        return await self._fallback.notify(briefing)

    async def play_audio(self, audio_path: str) -> NotificationResult:
        if self._send_command:
            try:
                result = await self._send_command("play_audio", {
                    "audio_path": audio_path,
                })
                if result.get("success"):
                    return NotificationResult(success=True, method="tauri_audio")
            except Exception as e:
                logger.warning("tauri_audio_playback_failed", error=str(e))
        
        return await self._fallback.play_audio(audio_path)


class CompositeNotifier(BriefingNotifier):
    """
    Composite notifier that tries multiple notifiers in order until one succeeds.
    """

    def __init__(self, notifiers: list[BriefingNotifier]):
        self.notifiers = notifiers

    async def notify(self, briefing: BriefingContent) -> NotificationResult:
        for notifier in self.notifiers:
            try:
                result = await notifier.notify(briefing)
                if result.success:
                    return result
            except Exception as e:
                logger.warning("notifier_failed", notifier=type(notifier).__name__, error=str(e))
        
        return NotificationResult(
            success=False,
            method="composite",
            error="All notifiers failed"
        )

    async def play_audio(self, audio_path: str) -> NotificationResult:
        for notifier in self.notifiers:
            try:
                result = await notifier.play_audio(audio_path)
                if result.success:
                    return result
            except Exception as e:
                logger.warning("notifier_audio_failed", notifier=type(notifier).__name__, error=str(e))
        
        return NotificationResult(
            success=False,
            method="composite",
            error="All audio notifiers failed"
        )


def create_default_notifier(
    tauri_send_command: Optional[Callable[[str, dict], Awaitable[dict]]] = None,
    use_console: bool = False,
) -> BriefingNotifier:
    """
    Create a default notifier chain.
    
    Order of preference:
    1. Tauri (if send_command provided)
    2. Console (if use_console=True)
    3. Logging (always available fallback)
    """
    notifiers = []
    
    if tauri_send_command:
        notifiers.append(TauriNotifier(tauri_send_command))
    
    if use_console:
        notifiers.append(ConsoleNotifier())
    
    notifiers.append(LoggingNotifier())
    
    return CompositeNotifier(notifiers)
