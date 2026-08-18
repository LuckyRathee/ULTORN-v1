"""
External service clients - STT, LLM, TTS, and action APIs.

Each service has typed error classes and explicit timeout handling.
"""

from .stt import transcribe_audio, STTError, STTResult
from .llm import extract_intent, LLMExtractionError, LLMExtractionResult
from .tts import synthesize_speech, TTSError
from .weather import get_weather, WeatherError
from .calendar import create_calendar_event, list_calendar_events, CalendarError
from .tasks import create_task, list_tasks, TaskError

__all__ = [
    # STT
    "transcribe_audio",
    "STTError",
    "STTResult",
    # LLM
    "extract_intent",
    "LLMExtractionError",
    "LLMExtractionResult",
    # TTS
    "synthesize_speech",
    "TTSError",
    # Weather
    "get_weather",
    "WeatherError",
    # Calendar
    "create_calendar_event",
    "list_calendar_events",
    "CalendarError",
    # Tasks
    "create_task",
    "list_tasks",
    "TaskError",
]