"""
Pipeline stage handlers - each stage is a pure async function: StateData -> StateData.

Stages:
1. audio_input - Validate and prepare audio data
2. transcription - Whisper STT (Groq API or local faster-whisper)
3. intent_extraction - LLM tool-calling to structured JSON
4. action_execution - Route intent to real API integration
5. response - Format result + optional TTS
"""

from .audio_input import handle_audio_input
from .transcription import handle_transcription
from .intent_extraction import handle_intent_extraction
from .action_execution import handle_action_execution
from .response import handle_response

__all__ = [
    "handle_audio_input",
    "handle_transcription",
    "handle_intent_extraction",
    "handle_action_execution",
    "handle_response",
]