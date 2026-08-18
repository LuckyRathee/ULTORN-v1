"""
Stage 3: Intent Extraction - LLM tool-calling to structured JSON.

Uses function-calling to guarantee valid schema output.
Returns discriminated union Intent type for type-safe routing.
"""

import time
import json
from typing import Optional
from pydantic import TypeAdapter

from ..state.states import StateData, PipelineState
from ..schemas.intent import Intent, IntentType, UnknownIntent
from ..schemas.api import IntentExtractionResponse
from ..services.llm import extract_intent, LLMExtractionError
from ..config import settings

# TypeAdapter for validating the discriminated union
IntentTypeAdapter = TypeAdapter(Intent)


# Minimum confidence threshold for accepting an intent
MIN_INTENT_CONFIDENCE = 0.5


async def handle_intent_extraction(state: StateData) -> StateData:
    """
    Stage 3 handler: Extract structured intent from transcript.
    
    Reads state.transcription.text, calls LLM with function-calling,
    validates against Intent schema, stores result.
    
    Transitions:
    - Valid intent + confidence >= threshold -> CONFIRMING_INTENT
    - Low confidence -> FAILED (INTENT_LOW_CONFIDENCE)
    - Malformed JSON / schema violation -> FAILED (INTENT_MALFORMED_JSON)
    - Unknown intent -> CONFIRMING_INTENT (with UnknownIntent, auto-fails at action)
    - LLM timeout/error -> FAILED (INTENT_LLM_TIMEOUT)
    
    Args:
        state: Current pipeline state with transcription
        
    Returns:
        Updated state with intent result
        
    Raises:
        RetryableError: For transient LLM failures (timeout, rate limit)
        NonRetryableError: For permanent failures (low confidence, schema violation)
    """
    if not state.transcription or not state.transcription.text:
        state.current_state = PipelineState.FAILED
        raise NonRetryableError("No transcription available for intent extraction")
    
    start_time = time.perf_counter()
    
    try:
        # Call LLM with function-calling for structured output
        result = await extract_intent(
            transcript=state.transcription.text,
            provider=settings.llm_provider,
            model=settings.intent_model,
        )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Parse and validate the intent
        intent = _parse_and_validate_intent(result.intent_json)
        
        # Check confidence
        if intent.confidence < MIN_INTENT_CONFIDENCE:
            state.current_state = PipelineState.FAILED
            raise NonRetryableError(
                f"INTENT_LOW_CONFIDENCE: Intent confidence {intent.confidence:.2f} "
                f"below threshold {MIN_INTENT_CONFIDENCE}"
            )
        
        # Store intent result
        state.intent = intent
        state.raw_llm_output = result.raw_output
        
        # Determine if confirmation needed (destructive actions)
        state.requires_confirmation = _requires_confirmation(intent)
        
        # Success - transition to confirmation
        state.current_state = PipelineState.CONFIRMING_INTENT
        return state
        
    except LLMExtractionError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        if e.error_type in ("timeout", "rate_limit", "server_error"):
            raise RetryableError(f"LLM transient error: {e}") from e
        else:
            raise NonRetryableError(f"LLM permanent error: {e}") from e
            
    except json.JSONDecodeError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise NonRetryableError(f"INTENT_MALFORMED_JSON: {e}") from e
        
    except ValueError as e:
        # Schema validation error
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise NonRetryableError(f"INTENT_SCHEMA_VIOLATION: {e}") from e
        
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise NonRetryableError(f"Intent extraction unexpected error: {e}") from e


def _parse_and_validate_intent(intent_json: dict) -> Intent:
    """
    Parse LLM output JSON and validate against Intent discriminated union.
    
    The LLM should return JSON matching one of the Intent models exactly.
    We use Pydantic's discriminated union validation via TypeAdapter.
    """
    # Use TypeAdapter to validate the discriminated union
    return IntentTypeAdapter.validate_python(intent_json)


def _requires_confirmation(intent: Intent) -> bool:
    """
    Determine if an intent requires user confirmation before execution.
    
    Destructive/modifying actions require confirmation.
    Read-only actions (weather, list) do not.
    """
    from ..schemas.intent import IntentType
    
    # Actions that modify state require confirmation
    confirming_types = {
        IntentType.CALENDAR_CREATE,
        IntentType.TASK_CREATE,
    }
    
    return intent.type in confirming_types


# Exception classes for this stage
class RetryableError(Exception):
    """Transient failure - can be retried."""
    pass


class NonRetryableError(Exception):
    """Permanent failure - should not be retried."""
    pass