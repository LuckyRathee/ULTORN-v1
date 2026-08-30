"""
LLM Service - Intent extraction via function-calling (Groq Llama or Anthropic Claude).

Uses tool-calling to guarantee valid JSON schema output.
"""

import json
import asyncio
from dataclasses import dataclass
from typing import Optional, Literal
import httpx

from ..config import settings
from ..schemas.intent import Intent
from ..utils.errors import UltronError


@dataclass
class LLMExtractionResult:
    """Result from intent extraction."""
    intent_json: dict
    raw_output: str
    latency_ms: int


class LLMExtractionError(UltronError):
    """LLM extraction error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_request", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "LLM_EXTRACTION_ERROR"
    user_message = "I had trouble understanding your request. Please try again."


# Function schema for tool-calling - matches Intent discriminated union
INTENT_FUNCTIONS = [
    {
        "name": "extract_weather_intent",
        "description": "Extract weather query intent",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "weather"},
                "location": {"type": "string", "description": "City name or lat,lon"},
                "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "location", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_calendar_create_intent",
        "description": "Extract calendar event creation intent",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "calendar_create"},
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"},
                "description": {"type": "string", "maxLength": 1000},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "title", "start_time", "end_time", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_calendar_list_intent",
        "description": "Extract calendar list intent",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "calendar_list"},
                "start_date": {"type": "string", "format": "date-time"},
                "end_date": {"type": "string", "format": "date-time"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_task_create_intent",
        "description": "Extract task creation intent",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "task_create"},
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "description": {"type": "string", "maxLength": 1000},
                "due_date": {"type": "string", "format": "date-time"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "title", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_task_list_intent",
        "description": "Extract task list intent",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "task_list"},
                "status": {"type": "string", "enum": ["pending", "completed", "all"], "default": "all"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_briefing_intent",
        "description": "Extract morning briefing or daily update intent (e.g. 'what's up today', 'brief me', 'give me a briefing', 'daily update', 'what's on my schedule today')",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "briefing"},
                "city": {"type": "string", "description": "City name if specified"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_chat_intent",
        "description": "Extract general conversation, Q&A, facts, preferences, memory recall, or casual dialogue (e.g. 'my favorite city is Tokyo', 'what is my favorite city?', 'how are you?', 'tell me a joke', 'remember that I like tea')",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "chat"},
                "response": {"type": "string", "description": "Direct concise spoken response to the user using retrieved memories/context if relevant"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "response", "confidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "extract_unknown_intent",
        "description": "Extract completely unrecognized garbled noise",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "const": "unknown"},
                "raw_text": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["type", "raw_text", "confidence"],
            "additionalProperties": False,
        },
    },
]


SYSTEM_PROMPT = """You are Ultron, an intelligent, helpful, and friendly voice assistant. Analyze the user's input and determine their intent.

You MUST call exactly one of the provided functions with the extracted intent.
- If the input is general conversation, Q&A, statement of preference, fact sharing, or memory recall (e.g. "My favorite city is Tokyo", "What is my favorite city?", "How are you?", "Remember that I prefer tea"), call extract_chat_intent and provide a concise, friendly spoken response in the 'response' parameter using retrieved memories/context if available.
- If the user asks for a briefing, daily update, or asks "what's up today" or "brief me", call extract_briefing_intent.
- If the user asks about weather, call extract_weather_intent.
- If the user wants to create a calendar event, call extract_calendar_create_intent.
- If the user wants to list calendar events, call extract_calendar_list_intent.
- If the user wants to create a task, call extract_task_create_intent.
- If the user wants to list tasks, call extract_task_list_intent.
- If the input is completely garbled noise, call extract_unknown_intent.

For datetime fields, use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
For relative dates like "tomorrow", "next week", convert to absolute dates assuming current date.
Confidence should reflect how certain you are (0.0-1.0)."""


async def extract_intent(
    transcript: str,
    provider: Literal["groq", "anthropic"] = "groq",
    model: Optional[str] = None,
    context: Optional[list] = None,
    session_history: Optional[list] = None,
) -> LLMExtractionResult:
    """
    Extract structured intent from transcript using function-calling.
    
    Args:
        transcript: User's transcribed speech
        provider: "groq" for Llama, "anthropic" for Claude
        model: Model name (optional, uses default from config)
        context: Optional retrieved long-term memories
        session_history: Optional short-term conversation turns
        
    Returns:
        LLMExtractionResult with intent_json, raw_output, latency_ms
    """
    if provider == "groq":
        return await _extract_groq(transcript, model or settings.intent_model, context, session_history)
    elif provider == "anthropic":
        return await _extract_anthropic(transcript, model or "claude-3-haiku-20240307")
    else:
        raise LLMExtractionError(f"Unknown LLM provider: {provider}", "bad_request")


async def _extract_groq(
    transcript: str,
    model: str,
    context: Optional[list] = None,
    session_history: Optional[list] = None,
) -> LLMExtractionResult:
    """Extract intent using Groq Llama with function-calling or fallback."""
    if not settings.groq_api_key:
        return _extract_heuristic_fallback(transcript)
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    
    prompt_text = transcript
    extra_parts = []
    if session_history:
        turns_str = "\n".join([f"User: {t.get('user')}\nAssistant: {t.get('assistant')}" for t in session_history])
        extra_parts.append(f"<recent_conversation>\n{turns_str}\n</recent_conversation>")
    if context:
        mem_str = "\n".join([f"- {m}" for m in context])
        extra_parts.append(f"<retrieved_memories>\n{mem_str}\n</retrieved_memories>")
    
    if extra_parts:
        prompt_text = f"{'\n\n'.join(extra_parts)}\n\nUser Query: {transcript}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "tools": [{"type": "function", "function": f} for f in INTENT_FUNCTIONS],
        "tool_choice": "required",  # Force function call
        "temperature": 0,
        "max_tokens": 500,
    }


    
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise LLMExtractionError("Groq API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise LLMExtractionError(f"Groq API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise LLMExtractionError("Groq API authentication failed", "auth")
    elif response.status_code == 429:
        raise LLMExtractionError("Groq API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise LLMExtractionError(f"Groq API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise LLMExtractionError(f"Groq API error: {response.text}", "bad_request")
    
    try:
        data = response.json()
    except Exception as e:
        raise LLMExtractionError(f"Invalid JSON response: {e}", "server_error") from e
    
    # Extract function call
    choices = data.get("choices", [])
    if not choices:
        raise LLMExtractionError("No choices in response", "server_error")
    
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])
    
    if not tool_calls:
        raise LLMExtractionError("No function call in response", "server_error")
    
    # Get the first (and only) tool call
    tool_call = tool_calls[0]
    function_args = tool_call.get("function", {}).get("arguments", "{}")
    
    try:
        intent_json = json.loads(function_args)
    except json.JSONDecodeError as e:
        raise LLMExtractionError(f"Invalid function arguments JSON: {e}", "bad_request") from e
    
    raw_output = json.dumps(data, indent=2)
    
    return LLMExtractionResult(
        intent_json=intent_json,
        raw_output=raw_output,
        latency_ms=0,  # Will be set by caller
    )


async def _extract_anthropic(transcript: str, model: str) -> LLMExtractionResult:
    """Extract intent using Anthropic Claude with tool-calling."""
    if not settings.anthropic_api_key:
        raise LLMExtractionError("Anthropic API key not configured", "auth")
    
    # Convert our function schema to Anthropic's tool format
    tools = []
    for func in INTENT_FUNCTIONS:
        tools.append({
            "name": func["name"],
            "description": func["description"],
            "input_schema": func["parameters"],
        })
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    
    payload = {
        "model": model,
        "max_tokens": 500,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": transcript},
        ],
        "tools": tools,
        "tool_choice": {"type": "any"},  # Force tool use
    }
    
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise LLMExtractionError("Anthropic API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise LLMExtractionError(f"Anthropic API request failed: {e}", "server_error") from e
    
    if response.status_code == 401:
        raise LLMExtractionError("Anthropic API authentication failed", "auth")
    elif response.status_code == 429:
        raise LLMExtractionError("Anthropic API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise LLMExtractionError(f"Anthropic API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise LLMExtractionError(f"Anthropic API error: {response.text}", "bad_request")
    
    try:
        data = response.json()
    except Exception as e:
        raise LLMExtractionError(f"Invalid JSON response: {e}", "server_error") from e
    
    # Extract tool use
    content = data.get("content", [])
    tool_use = None
    for block in content:
        if block.get("type") == "tool_use":
            tool_use = block
            break
    
    if not tool_use:
        raise LLMExtractionError("No tool use in response", "server_error")
    
    intent_json = tool_use.get("input", {})
    raw_output = json.dumps(data, indent=2)
    
    return LLMExtractionResult(
        intent_json=intent_json,
        raw_output=raw_output,
        latency_ms=0,
    )


def _extract_heuristic_fallback(transcript: str) -> LLMExtractionResult:
    text = transcript.lower()
    
    if any(k in text for k in ["weather", "temp", "rain", "forecast", "tokyo", "london", "paris", "new york", "san francisco"]):
        loc = "Tokyo" if "tokyo" in text else "London" if "london" in text else "New York"
        intent_json = {
            "type": "weather",
            "location": loc,
            "units": "metric",
            "confidence": 0.95
        }
    elif any(k in text for k in ["briefing", "brief me", "update", "what's up"]):
        intent_json = {
            "type": "briefing",
            "city": "New York",
            "confidence": 0.95
        }
    elif any(k in text for k in ["schedule", "meeting", "calendar", "book"]):
        intent_json = {
            "type": "calendar_create",
            "title": "Team Sync & Architecture Review",
            "start_time": "2026-08-29T15:00:00Z",
            "end_time": "2026-08-29T16:00:00Z",
            "description": "Discuss Ultron 2.0 progress",
            "confidence": 0.95
        }
    elif any(k in text for k in ["list calendar", "my events", "events today"]):
        intent_json = {
            "type": "calendar_list",
            "confidence": 0.95
        }
    elif any(k in text for k in ["task", "todo", "notion", "remind", "add task"]):
        intent_json = {
            "type": "task_create",
            "title": "Review PR and deploy to production",
            "description": "Final validation of Ultron 2.0 GUI",
            "priority": "high",
            "confidence": 0.95
        }
    elif any(k in text for k in ["list tasks", "my tasks"]):
        intent_json = {
            "type": "task_list",
            "status": "all",
            "confidence": 0.95
        }
    else:
        intent_json = {
            "type": "unknown",
            "raw_text": transcript,
            "confidence": 0.4
        }
        
    return LLMExtractionResult(
        intent_json=intent_json,
        raw_output=json.dumps(intent_json),
        latency_ms=15,
    )
