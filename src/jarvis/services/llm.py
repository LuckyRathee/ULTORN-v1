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
from ..utils.errors import JarvisError


@dataclass
class LLMExtractionResult:
    """Result from intent extraction."""
    intent_json: dict
    raw_output: str
    latency_ms: int


class LLMExtractionError(JarvisError):
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
        "name": "extract_unknown_intent",
        "description": "Extract unknown/ambiguous intent",
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


SYSTEM_PROMPT = """You are an intent extraction system. Analyze the user's transcript and determine their intent.

You MUST call exactly one of the provided functions with the extracted intent.
- If the user asks about weather, call extract_weather_intent
- If the user wants to create a calendar event, call extract_calendar_create_intent
- If the user wants to list calendar events, call extract_calendar_list_intent
- If the user wants to create a task, call extract_task_create_intent
- If the user wants to list tasks, call extract_task_list_intent
- If the intent is unclear or doesn't match any category, call extract_unknown_intent

For datetime fields, use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
For relative dates like "tomorrow", "next week", convert to absolute dates assuming current date.
Confidence should reflect how certain you are (0.0-1.0)."""


async def extract_intent(
    transcript: str,
    provider: Literal["groq", "anthropic"] = "groq",
    model: Optional[str] = None,
) -> LLMExtractionResult:
    """
    Extract structured intent from transcript using function-calling.
    
    Args:
        transcript: User's transcribed speech
        provider: "groq" for Llama, "anthropic" for Claude
        model: Model name (optional, uses default from config)
        
    Returns:
        LLMExtractionResult with intent_json, raw_output, latency_ms
        
    Raises:
        LLMExtractionError: With typed error_type
    """
    if provider == "groq":
        return await _extract_groq(transcript, model or settings.intent_model)
    elif provider == "anthropic":
        return await _extract_anthropic(transcript, model or "claude-3-haiku-20240307")
    else:
        raise LLMExtractionError(f"Unknown LLM provider: {provider}", "bad_request")


async def _extract_groq(transcript: str, model: str) -> LLMExtractionResult:
    """Extract intent using Groq Llama with function-calling."""
    if not settings.groq_api_key:
        raise LLMExtractionError("Groq API key not configured", "auth")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
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