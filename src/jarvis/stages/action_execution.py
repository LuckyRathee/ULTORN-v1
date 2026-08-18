"""
Stage 4: Action Execution - Route intent to real API integration.

Dispatches to appropriate service based on intent type.
Each action has explicit error handling with typed errors.
"""

import time
from typing import Optional

from ..state.states import StateData, PipelineState
from ..schemas.intent import Intent, IntentType
from ..schemas.api import ActionResult
from ..services.weather import get_weather, WeatherError
from ..services.calendar import create_calendar_event, list_calendar_events, CalendarError
from ..services.tasks import create_task, list_tasks, TaskError
from ..config import settings


async def handle_action_execution(state: StateData) -> StateData:
    """
    Stage 4 handler: Execute the action for the extracted intent.
    
    Routes to appropriate service based on intent.type.
    Each service returns typed result with success/error.
    
    Transitions:
    - Success -> RESPONDING
    - Failure (typed error) -> FAILED
    
    Args:
        state: Current pipeline state with intent
        
    Returns:
        Updated state with action_result
        
    Raises:
        NonRetryableError: For all action failures (typed errors surfaced to user)
    """
    if not state.intent:
        state.current_state = PipelineState.FAILED
        raise NonRetryableError("No intent available for action execution")
    
    start_time = time.perf_counter()
    
    try:
        # Route to appropriate handler based on intent type
        intent = state.intent
        
        if intent.type == IntentType.WEATHER:
            result = await _execute_weather(intent)
        elif intent.type == IntentType.CALENDAR_CREATE:
            result = await _execute_calendar_create(intent)
        elif intent.type == IntentType.CALENDAR_LIST:
            result = await _execute_calendar_list(intent)
        elif intent.type == IntentType.TASK_CREATE:
            result = await _execute_task_create(intent)
        elif intent.type == IntentType.TASK_LIST:
            result = await _execute_task_list(intent)
        elif intent.type == IntentType.UNKNOWN:
            result = ActionResult(
                success=False,
                error="I didn't understand that request. Could you rephrase?",
                error_type="bad_params",
                latency_ms=0,
            )
        else:
            result = ActionResult(
                success=False,
                error=f"Unsupported intent type: {intent.type}",
                error_type="bad_params",
                latency_ms=0,
            )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        result.latency_ms = latency_ms
        
        # Store action result
        state.action_result = result
        
        # Transition based on success
        if result.success:
            state.current_state = PipelineState.RESPONDING
        else:
            state.current_state = PipelineState.FAILED
            # Don't raise - let response stage handle the error message
            # But we need to signal failure
            raise NonRetryableError(result.error or "Action failed")
        
        return state
        
    except (WeatherError, CalendarError, TaskError) as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        state.action_result = ActionResult(
            success=False,
            error=str(e),
            error_type=e.error_type,
            latency_ms=latency_ms,
        )
        state.current_state = PipelineState.FAILED
        raise NonRetryableError(str(e)) from e
        
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        state.action_result = ActionResult(
            success=False,
            error=f"Unexpected error: {e}",
            error_type="unknown",
            latency_ms=latency_ms,
        )
        state.current_state = PipelineState.FAILED
        raise NonRetryableError(f"Action execution unexpected error: {e}") from e


async def _execute_weather(intent) -> ActionResult:
    """Execute weather intent."""
    from ..schemas.intent import WeatherIntent
    weather_intent: WeatherIntent = intent
    data = await get_weather(weather_intent.location, weather_intent.units)
    return ActionResult(success=True, data=data, error=None, error_type=None, latency_ms=0)


async def _execute_calendar_create(intent) -> ActionResult:
    """Execute calendar create intent."""
    from ..schemas.intent import CalendarCreateIntent
    cal_intent: CalendarCreateIntent = intent
    data = await create_calendar_event(
        title=cal_intent.title,
        start_time=cal_intent.start_time,
        end_time=cal_intent.end_time,
        description=cal_intent.description,
    )
    return ActionResult(success=True, data=data, error=None, error_type=None, latency_ms=0)


async def _execute_calendar_list(intent) -> ActionResult:
    """Execute calendar list intent."""
    from ..schemas.intent import CalendarListIntent
    cal_intent: CalendarListIntent = intent
    data = await list_calendar_events(cal_intent.start_date, cal_intent.end_date)
    return ActionResult(success=True, data=data, error=None, error_type=None, latency_ms=0)


async def _execute_task_create(intent) -> ActionResult:
    """Execute task create intent."""
    from ..schemas.intent import TaskCreateIntent
    task_intent: TaskCreateIntent = intent
    data = await create_task(
        title=task_intent.title,
        description=task_intent.description,
        due_date=task_intent.due_date,
        priority=task_intent.priority,
    )
    return ActionResult(success=True, data=data, error=None, error_type=None, latency_ms=0)


async def _execute_task_list(intent) -> ActionResult:
    """Execute task list intent."""
    from ..schemas.intent import TaskListIntent
    task_intent: TaskListIntent = intent
    data = await list_tasks(task_intent.status)
    return ActionResult(success=True, data=data, error=None, error_type=None, latency_ms=0)


# Exception classes for this stage
class NonRetryableError(Exception):
    """Permanent failure - should not be retried. Error is surfaced to user."""
    pass