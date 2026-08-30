"""
TTS Audio Caching for Daily Briefings.
"""

import hashlib
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cached TTS audio entry."""
    key: str
    text: str
    audio_path: str
    provider: str
    voice_id: Optional[str]
    created_at: str
    expires_at: str
    length_chars: int


class TTSCache:
    """Cache for TTS audio files to avoid regenerating identical content."""

    def __init__(
        self,
        cache_dir: str = "./scratch/tts_cache",
        max_age_days: int = 7,
        max_size_mb: int = 100,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self._index_path = self.cache_dir / "index.json"
        self._index: dict[str, CacheEntry] = {}
        self._load_index()

    def _load_index(self):
        """Load cache index from disk."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r") as f:
                    data = json.load(f)
                    self._index = {
                        k: CacheEntry(**v) for k, v in data.items()
                    }
                logger.info("tts_cache_index_loaded", entries=len(self._index))
            except Exception as e:
                logger.warning("tts_cache_index_load_failed", error=str(e))
                self._index = {}

    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self._index_path, "w") as f:
                json.dump(
                    {k: asdict(v) for k, v in self._index.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error("tts_cache_index_save_failed", error=str(e))

    def _generate_key(self, text: str, provider: str, voice_id: Optional[str]) -> str:
        """Generate a cache key from text and TTS parameters."""
        content = f"{text}|{provider}|{voice_id or 'default'}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, text: str, provider: str, voice_id: Optional[str] = None) -> Optional[str]:
        """
        Get cached audio file path if exists and not expired.
        
        Returns:
            Path to cached audio file, or None if not cached/expired.
        """
        key = self._generate_key(text, provider, voice_id)
        
        if key not in self._index:
            return None
        
        entry = self._index[key]
        
        # Check expiration
        if datetime.fromisoformat(entry.expires_at) < datetime.utcnow():
            self._remove_entry(key)
            return None
        
        # Verify file exists
        audio_path = Path(entry.audio_path)
        if not audio_path.exists():
            self._remove_entry(key)
            return None
        
        logger.info("tts_cache_hit", key=key[:8])
        return entry.audio_path

    def put(
        self,
        text: str,
        provider: str,
        audio_path: str,
        voice_id: Optional[str] = None,
    ) -> str:
        """
        Add audio file to cache.
        
        Args:
            text: The text that was synthesized
            provider: TTS provider name
            audio_path: Path to the generated audio file
            voice_id: Optional voice identifier
            
        Returns:
            Cache key
        """
        key = self._generate_key(text, provider, voice_id)
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.max_age_days)
        
        # Copy audio file to cache directory
        cached_filename = f"{key}.mp3"
        cached_path = self.cache_dir / cached_filename
        
        try:
            import shutil
            shutil.copy2(audio_path, cached_path)
        except Exception as e:
            logger.error("tts_cache_copy_failed", error=str(e))
            return key
        
        entry = CacheEntry(
            key=key,
            text=text,
            audio_path=str(cached_path),
            provider=provider,
            voice_id=voice_id,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            length_chars=len(text),
        )
        
        self._index[key] = entry
        self._save_index()
        self._enforce_size_limit()
        
        logger.info("tts_cache_stored", key=key[:8], size_mb=cached_path.stat().st_size / 1024 / 1024)
        return key

    def _remove_entry(self, key: str):
        """Remove a cache entry and its audio file."""
        if key in self._index:
            entry = self._index[key]
            try:
                Path(entry.audio_path).unlink(missing_ok=True)
            except Exception:
                pass
            del self._index[key]
            self._save_index()

    def _enforce_size_limit(self):
        """Remove oldest entries if cache exceeds size limit."""
        total_size = sum(
            Path(e.audio_path).stat().st_size
            for e in self._index.values()
            if Path(e.audio_path).exists()
        )
        
        max_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size > max_bytes:
            # Sort by creation time, oldest first
            sorted_entries = sorted(
                self._index.items(),
                key=lambda x: x[1].created_at
            )
            
            for key, entry in sorted_entries:
                if total_size <= max_bytes * 0.8:  # Keep 80% headroom
                    break
                self._remove_entry(key)
                if Path(entry.audio_path).exists():
                    total_size -= Path(entry.audio_path).stat().st_size
            
            logger.info("tts_cache_size_enforced", remaining_mb=total_size / 1024 / 1024)

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._index.items()
            if datetime.fromisoformat(entry.expires_at) < now
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.info("tts_cache_expired_cleaned", count=len(expired_keys))
        
        return len(expired_keys)

    def clear(self):
        """Clear entire cache."""
        for key in list(self._index.keys()):
            self._remove_entry(key)
        logger.info("tts_cache_cleared")


# Global cache instance
_tts_cache: Optional[TTSCache] = None


def get_tts_cache() -> TTSCache:
    """Get or create the global TTS cache instance."""
    global _tts_cache
    if _tts_cache is None:
        _tts_cache = TTSCache()
    return _tts_cache
