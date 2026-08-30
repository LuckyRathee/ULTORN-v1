"""
Utility modules - errors, audio processing, logging.
"""

from .errors import (
    UltronError,
    AudioError,
    TranscriptionError,
    IntentExtractionError,
    ActionExecutionError,
    TTSError,
    PipelineError,
)
from .audio import validate_audio, convert_to_wav, AudioValidation
from .logging import setup_logging, get_logger

__all__ = [
    # Errors
    "UltronError",
    "AudioError",
    "TranscriptionError",
    "IntentExtractionError",
    "ActionExecutionError",
    "TTSError",
    "PipelineError",
    # Audio
    "validate_audio",
    "convert_to_wav",
    "AudioValidation",
    # Logging
    "setup_logging",
    "get_logger",
]
