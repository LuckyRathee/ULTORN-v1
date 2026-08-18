"""
Stage 5: Response - Format result + optional TTS.

Generates human-readable response text and optionally synthesizes speech.
"""

import time
from typing import Optional

from ..state.states import StateData, PipelineState
from ..schemas.api import PipelineResponse, ActionResult
from ..services.tts import synthesize_speech, TTSError
from ..config import settings


async def handle_response(state: StateData) -> StateData:
    """
    Stage 5 handler: Format final response for the user.
    
    Generates response_text from action_result, optionally generates TTS audio.
    
    Transitions:
    - Success -> DONE
    - TTS failure (non-blocking) -> DONE (with text only)
    
    Args:
        state: Current pipeline state with action_result
        
    Returns:
        Updated state with response_text and optional audio_url
    """
    start_time = time.perf_counter()
    
    try:
        # Generate response text
        response_text = _format_response(state)
        state.response_text = response_text
        
        # Generate TTS if enabled and action succeeded
        if settings.tts_provider != "none" and state.action_result and state.action_result.success:
            try:
                audio_url = await synthesize_speech(
                    text=response_text,
                    provider=settings.tts_provider,
                    voice_id=settings.elevenlabs_voice_id,
                )
                state.audio_url = audio_url
            except TTSError as e:
                # TTS failure is non-blocking - log and continue with text only
                # In production, you'd log this
                pass
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Success - transition to DONE
        state.current_state = PipelineState.DONE
        return state
        
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        # Response formatting should never fail, but if it does:
        state.response_text = "I encountered an error generating the response."
        state.current_state = PipelineState.DONE  # Still DONE, just with error message
        return state


def _format_response(state: StateData) -> str:
    """
    Format a human-readable response from the pipeline state.
    
    Handles both success and failure cases.
    """
    # If pipeline failed at an earlier stage, use the error
    if state.error:
        return _format_error_response(state)
    
    # If action failed, use action error
    if state.action_result and not state.action_result.success:
        return _format_action_error(state.action_result)
    
    # Success - format based on intent type
    if not state.intent:
        return "I processed your request but couldn't determine the intent."
    
    from ..schemas.intent import IntentType
    
    if state.intent.type == IntentType.WEATHER:
        return _format_weather_response(state.action_result.data)
    elif state.intent.type == IntentType.CALENDAR_CREATE:
        return _format_calendar_create_response(state.action_result.data)
    elif state.intent.type == IntentType.CALENDAR_LIST:
        return _format_calendar_list_response(state.action_result.data)
    elif state.intent.type == IntentType.TASK_CREATE:
        return _format_task_create_response(state.action_result.data)
    elif state.intent.type == IntentType.TASK_LIST:
        return _format_task_list_response(state.action_result.data)
    else:
        return "Your request has been processed."


def _format_error_response(state: StateData) -> str:
    """Format error response for user."""
    error_messages = {
        "AUDIO_NO_INPUT": "I didn't receive any audio. Please try again.",
        "AUDIO_INVALID_FORMAT": "The audio format isn't supported. Please use WAV, MP3, or M4A.",
        "AUDIO_TOO_LARGE": "The audio file is too large. Please keep it under 25MB.",
        "STT_NO_SPEECH": "I couldn't detect any speech in the audio. Please speak clearly.",
        "STT_LOW_CONFIDENCE": "I had trouble understanding the audio. Could you repeat that?",
        "INTENT_LOW_CONFIDENCE": "I'm not sure what you're asking for. Could you rephrase?",
        "INTENT_MALFORMED_JSON": "I had trouble parsing your request. Please try again.",
        "INTENT_SCHEMA_VIOLATION": "I couldn't understand the structure of your request.",
    }
    
    # Try to match error type
    if state.error_type and state.error_type in error_messages:
        return error_messages[state.error_type]
    
    # Generic fallback
    return f"Sorry, I encountered an error: {state.error}"


def _format_action_error(action_result: ActionResult) -> str:
    """Format action-specific error for user."""
    error_messages = {
        "timeout": "The request timed out. Please try again.",
        "auth": "There's an authentication issue with the service. Please check your settings.",
        "bad_params": "I couldn't process that request. Please check the details and try again.",
        "api_down": "The service is currently unavailable. Please try again later.",
        "unknown": "An unexpected error occurred. Please try again.",
    }
    
    if action_result.error_type and action_result.error_type in error_messages:
        return error_messages[action_result.error_type]
    
    return action_result.error or "An error occurred while processing your request."


def _format_weather_response(data: dict) -> str:
    """Format weather data into natural language."""
    if not data:
        return "I couldn't retrieve the weather information."
    
    location = data.get("location", "the requested location")
    temp = data.get("temperature")
    condition = data.get("condition", "unknown conditions")
    humidity = data.get("humidity")
    wind = data.get("wind_kph")
    
    parts = [f"The weather in {location} is {condition}"]
    
    if temp is not None:
        parts.append(f"with a temperature of {temp}°C")
    
    if humidity is not None:
        parts.append(f"and {humidity}% humidity")
    
    if wind is not None:
        parts.append(f"with winds at {wind} km/h")
    
    return ". ".join(parts) + "."


def _format_calendar_create_response(data: dict) -> str:
    """Format calendar create response."""
    if not data:
        return "The event was created successfully."
    
    title = data.get("title", "the event")
    start = data.get("start_time", "")
    return f"Created '{title}' for {start}."


def _format_calendar_list_response(data: dict) -> str:
    """Format calendar list response."""
    if not data or not data.get("events"):
        return "You have no upcoming events."
    
    events = data["events"]
    if len(events) == 1:
        event = events[0]
        return f"You have one event: {event.get('title', 'Untitled')} at {event.get('start_time', 'unknown time')}."
    
    lines = [f"You have {len(events)} upcoming events:"]
    for event in events[:5]:  # Limit to 5
        lines.append(f"• {event.get('title', 'Untitled')} at {event.get('start_time', 'unknown time')}")
    
    if len(events) > 5:
        lines.append(f"... and {len(events) - 5} more")
    
    return "\n".join(lines)


def _format_task_create_response(data: dict) -> str:
    """Format task create response."""
    if not data:
        return "The task was created successfully."
    
    title = data.get("title", "the task")
    return f"Created task: '{title}'."


def _format_task_list_response(data: dict) -> str:
    """Format task list response."""
    if not data or not data.get("tasks"):
        return "You have no tasks."
    
    tasks = data["tasks"]
    if len(tasks) == 1:
        task = tasks[0]
        status = "✓" if task.get("completed") else "○"
        return f"{status} {task.get('title', 'Untitled')}"
    
    lines = [f"You have {len(tasks)} tasks:"]
    for task in tasks[:10]:  # Limit to 10
        status = "✓" if task.get("completed") else "○"
        lines.append(f"{status} {task.get('title', 'Untitled')}")
    
    if len(tasks) > 10:
        lines.append(f"... and {len(tasks) - 10} more")
    
    return "\n".join(lines)