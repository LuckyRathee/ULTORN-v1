"""
State machine orchestration for the 5-stage pipeline.

Handles explicit transitions, error handling, and retry logic.
No recursive retries - explicit max-retry with backoff for transient errors only.
"""

from typing import Callable, Awaitable, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .states import PipelineState, StateData
from ..schemas.pipeline import StageStatus


class TransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, from_state: PipelineState, to_state: PipelineState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition: {from_state} -> {to_state}")


class RetryableError(Exception):
    """Base class for errors that warrant a retry (transient failures)."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT be retried (permanent failures)."""
    pass


# Valid state transitions
VALID_TRANSITIONS: dict[PipelineState, set[PipelineState]] = {
    PipelineState.LISTENING: {PipelineState.TRANSCRIBING, PipelineState.FAILED},
    PipelineState.TRANSCRIBING: {PipelineState.EXTRACTING_INTENT, PipelineState.FAILED},
    PipelineState.EXTRACTING_INTENT: {PipelineState.CONFIRMING_INTENT, PipelineState.FAILED},
    PipelineState.CONFIRMING_INTENT: {PipelineState.EXECUTING, PipelineState.FAILED},
    PipelineState.EXECUTING: {PipelineState.RESPONDING, PipelineState.FAILED},
    PipelineState.RESPONDING: {PipelineState.DONE, PipelineState.FAILED},
    PipelineState.DONE: set(),
    PipelineState.FAILED: set(),
}


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""
    name: str
    max_retries: int = 2
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,)
    timeout_seconds: float = 30.0


class StateMachine:
    """
    Orchestrates the 5-stage pipeline with explicit state transitions.
    
    Each stage is an async function: StateData -> StateData
    The machine handles transitions, retries, timeouts, and logging.
    """
    
    def __init__(self, stage_configs: Optional[dict[str, StageConfig]] = None):
        self.stage_configs = stage_configs or {}
        self._stage_handlers: dict[PipelineState, Callable[[StateData], Awaitable[StateData]]] = {}
    
    def register_handler(self, state: PipelineState, handler: Callable[[StateData], Awaitable[StateData]]) -> None:
        """Register an async handler for a pipeline state."""
        self._stage_handlers[state] = handler
    
    def _validate_transition(self, from_state: PipelineState, to_state: PipelineState) -> None:
        """Validate that a state transition is allowed."""
        if to_state not in VALID_TRANSITIONS.get(from_state, set()):
            raise TransitionError(from_state, to_state)
    
    async def _execute_with_retry(
        self,
        handler: Callable[[StateData], Awaitable[StateData]],
        state_data: StateData,
        config: StageConfig,
    ) -> StateData:
        """Execute a stage handler with retry logic for transient errors."""
        
        @retry(
            stop=stop_after_attempt(config.max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(config.retryable_exceptions),
            reraise=True,
        )
        async def _run_with_timeout() -> StateData:
            try:
                return await asyncio.wait_for(
                    handler(state_data),
                    timeout=config.timeout_seconds,
                )
            except asyncio.TimeoutError as e:
                raise RetryableError(f"Stage {config.name} timed out after {config.timeout_seconds}s") from e
        
        return await _run_with_timeout()
    
    async def run(self, initial_data: StateData) -> StateData:
        """
        Run the pipeline from the initial state to completion.
        
        Returns the final StateData with all stage results populated.
        """
        current_state = initial_data.current_state
        state_data = initial_data
        
        while current_state not in (PipelineState.DONE, PipelineState.FAILED):
            # Get handler for current state
            handler = self._stage_handlers.get(current_state)
            if not handler:
                raise RuntimeError(f"No handler registered for state: {current_state}")
            
            # Get stage config
            config = self.stage_configs.get(current_state.value, StageConfig(name=current_state.value))
            
            # Mark stage as running
            state_data.mark_stage_start(config.name)
            state_data.current_state = current_state
            
            try:
                # Execute stage with retry logic
                start_time = time.perf_counter()
                state_data = await self._execute_with_retry(handler, state_data, config)
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Determine next state from handler's output
                next_state = state_data.current_state
                self._validate_transition(current_state, next_state)
                
                # Mark stage success
                state_data.mark_stage_success(config.name, {}, latency_ms)
                current_state = next_state
                
            except RetryableError as e:
                # Transient error - retries exhausted
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                state_data.mark_stage_failed(config.name, str(e), latency_ms, "transient_failure")
                state_data.current_state = PipelineState.FAILED
                current_state = PipelineState.FAILED
                
            except NonRetryableError as e:
                # Permanent error - fail fast
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                state_data.mark_stage_failed(config.name, str(e), latency_ms, "permanent_failure")
                state_data.current_state = PipelineState.FAILED
                current_state = PipelineState.FAILED
                
            except TransitionError as e:
                # Invalid transition - programming error
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                state_data.mark_stage_failed(config.name, str(e), latency_ms, "invalid_transition")
                state_data.current_state = PipelineState.FAILED
                current_state = PipelineState.FAILED
                
            except Exception as e:
                # Unexpected error - treat as non-retryable
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                state_data.mark_stage_failed(config.name, f"Unexpected error: {e}", latency_ms, "unknown")
                state_data.current_state = PipelineState.FAILED
                current_state = PipelineState.FAILED
        
        # Mark pipeline complete
        final_status = "done" if current_state == PipelineState.DONE else "failed"
        state_data.run.mark_completed(final_status)
        
        return state_data