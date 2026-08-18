"""
Typed exception classes for the Jarvis pipeline.

Each error has a code for programmatic handling and a user_message for display.
"""

from typing import Optional


class JarvisError(Exception):
    """Base exception with error code and user-friendly message."""
    code: str = "JARVIS_ERROR"
    user_message: str = "An error occurred. Please try again."
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "code": self.code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
        }


# Audio Errors
class AudioError(JarvisError):
    """Audio input/processing errors."""
    code = "AUDIO_ERROR"
    user_message = "There was a problem with the audio input."


class AudioNoInputError(AudioError):
    code = "AUDIO_NO_INPUT"
    user_message = "I didn't receive any audio. Please try again."


class AudioInvalidFormatError(AudioError):
    code = "AUDIO_INVALID_FORMAT"
    user_message = "The audio format isn't supported. Please use WAV, MP3, or M4A."


class AudioTooLargeError(AudioError):
    code = "AUDIO_TOO_LARGE"
    user_message = "The audio file is too large. Please keep it under 25MB."


class AudioInvalidBase64Error(AudioError):
    code = "AUDIO_INVALID_BASE64"
    user_message = "The audio data is corrupted. Please try again."


class AudioUnsupportedFormatError(AudioError):
    code = "AUDIO_UNSUPPORTED_FORMAT"
    user_message = "This audio format isn't supported. Please use WAV, MP3, M4A, OGG, or FLAC."


class AudioConversionError(AudioError):
    code = "AUDIO_CONVERSION_ERROR"
    user_message = "I couldn't process the audio format. Please try a different file."


# Transcription Errors
class TranscriptionError(JarvisError):
    """Speech-to-text errors."""
    code = "TRANSCRIPTION_ERROR"
    user_message = "I had trouble transcribing the audio. Please try again."


class TranscriptionNoSpeechError(TranscriptionError):
    code = "STT_NO_SPEECH"
    user_message = "I couldn't detect any speech in the audio. Please speak clearly."


class TranscriptionLowConfidenceError(TranscriptionError):
    code = "STT_LOW_CONFIDENCE"
    user_message = "I had trouble understanding the audio. Could you repeat that?"


class TranscriptionTimeoutError(TranscriptionError):
    code = "STT_TIMEOUT"
    user_message = "The transcription took too long. Please try again."


class TranscriptionAPIError(TranscriptionError):
    code = "STT_API_ERROR"
    user_message = "The transcription service is unavailable. Please try again later."


# Intent Extraction Errors
class IntentExtractionError(JarvisError):
    """Intent extraction/parsing errors."""
    code = "INTENT_EXTRACTION_ERROR"
    user_message = "I had trouble understanding your request. Please try again."


class IntentLowConfidenceError(IntentExtractionError):
    code = "INTENT_LOW_CONFIDENCE"
    user_message = "I'm not sure what you're asking for. Could you rephrase?"


class IntentMalformedJSONError(IntentExtractionError):
    code = "INTENT_MALFORMED_JSON"
    user_message = "I had trouble parsing your request. Please try again."


class IntentSchemaViolationError(IntentExtractionError):
    code = "INTENT_SCHEMA_VIOLATION"
    user_message = "I couldn't understand the structure of your request."


class IntentUnknownError(IntentExtractionError):
    code = "INTENT_UNKNOWN"
    user_message = "I didn't understand that request. Could you rephrase?"


class IntentLLMTimeoutError(IntentExtractionError):
    code = "INTENT_LLM_TIMEOUT"
    user_message = "The request took too long to process. Please try again."


# Action Execution Errors
class ActionExecutionError(JarvisError):
    """Action execution errors."""
    code = "ACTION_EXECUTION_ERROR"
    user_message = "I couldn't complete that action. Please try again."


class ActionTimeoutError(ActionExecutionError):
    code = "ACTION_TIMEOUT"
    user_message = "The request timed out. Please try again."


class ActionAuthError(ActionExecutionError):
    code = "ACTION_AUTH_FAILED"
    user_message = "There's an authentication issue. Please check your settings."


class ActionBadParamsError(ActionExecutionError):
    code = "ACTION_BAD_PARAMS"
    user_message = "I couldn't process that request. Please check the details and try again."


class ActionAPIDownError(ActionExecutionError):
    code = "ACTION_API_DOWN"
    user_message = "The service is currently unavailable. Please try again later."


class ActionValidationError(ActionExecutionError):
    code = "ACTION_VALIDATION_FAILED"
    user_message = "The request parameters are invalid. Please try again."


# TTS Errors
class TTSError(JarvisError):
    """Text-to-speech errors."""
    code = "TTS_ERROR"
    user_message = "I couldn't generate the audio response."


class TTSTimeoutError(TTSError):
    code = "TTS_TIMEOUT"
    user_message = "Audio generation timed out."


class TTSAPIError(TTSError):
    code = "TTS_API_ERROR"
    user_message = "The audio service is unavailable."


# Pipeline Errors
class PipelineError(JarvisError):
    """Pipeline orchestration errors."""
    code = "PIPELINE_ERROR"
    user_message = "An error occurred while processing your request."


class PipelineInvalidTransitionError(PipelineError):
    code = "PIPELINE_INVALID_TRANSITION"
    user_message = "Internal error: invalid pipeline state."


class PipelineStageNotFoundError(PipelineError):
    code = "PIPELINE_STAGE_NOT_FOUND"
    user_message = "Internal error: pipeline stage not configured."


# Error code to exception class mapping for easy lookup
ERROR_CODE_MAP = {
    # Audio
    "AUDIO_NO_INPUT": AudioNoInputError,
    "AUDIO_INVALID_FORMAT": AudioInvalidFormatError,
    "AUDIO_TOO_LARGE": AudioTooLargeError,
    "AUDIO_INVALID_BASE64": AudioInvalidBase64Error,
    "AUDIO_UNSUPPORTED_FORMAT": AudioUnsupportedFormatError,
    "AUDIO_CONVERSION_ERROR": AudioConversionError,
    # Transcription
    "STT_NO_SPEECH": TranscriptionNoSpeechError,
    "STT_LOW_CONFIDENCE": TranscriptionLowConfidenceError,
    "STT_TIMEOUT": TranscriptionTimeoutError,
    "STT_API_ERROR": TranscriptionAPIError,
    # Intent
    "INTENT_LOW_CONFIDENCE": IntentLowConfidenceError,
    "INTENT_MALFORMED_JSON": IntentMalformedJSONError,
    "INTENT_SCHEMA_VIOLATION": IntentSchemaViolationError,
    "INTENT_UNKNOWN": IntentUnknownError,
    "INTENT_LLM_TIMEOUT": IntentLLMTimeoutError,
    # Action
    "ACTION_TIMEOUT": ActionTimeoutError,
    "ACTION_AUTH_FAILED": ActionAuthError,
    "ACTION_BAD_PARAMS": ActionBadParamsError,
    "ACTION_API_DOWN": ActionAPIDownError,
    "ACTION_VALIDATION_FAILED": ActionValidationError,
    # TTS
    "TTS_TIMEOUT": TTSTimeoutError,
    "TTS_API_ERROR": TTSAPIError,
    # Pipeline
    "PIPELINE_INVALID_TRANSITION": PipelineInvalidTransitionError,
    "PIPELINE_STAGE_NOT_FOUND": PipelineStageNotFoundError,
}


def create_error_from_code(code: str, message: str, details: Optional[dict] = None) -> JarvisError:
    """Create appropriate error instance from error code."""
    error_class = ERROR_CODE_MAP.get(code, JarvisError)
    return error_class(message, details)