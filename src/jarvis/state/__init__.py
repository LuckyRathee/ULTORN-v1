"""
State machine implementation for the 5-stage pipeline.

Exports:
- PipelineState enum
- StateData class for carrying data between stages
- StateMachine class for orchestrating transitions
"""

from .states import PipelineState, StateData
from .machine import StateMachine, TransitionError

__all__ = [
    "PipelineState",
    "StateData",
    "StateMachine",
    "TransitionError",
]