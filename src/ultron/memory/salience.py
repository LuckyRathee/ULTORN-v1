"""
Salience scoring heuristics to evaluate memory persistence.
"""

import re
from .models import ConversationTurn, MemoryEntry


SALIENCE_TRIGGERS = [
    r"\b(my name is|i like|i prefer|i live in|my favorite|remember that|don't forget)\b",
    r"\b(remind me|my email is|my phone is|my address is|always|never)\b",
    r"\b(schedule|meeting|appointment|task|todo)\b",
]


def evaluate_salience(turn: ConversationTurn) -> float:
    """
    Calculate a salience score from 0.0 to 1.0 for a conversation turn.
    Returns >0.5 if turn should be saved to long-term vector store.
    """
    score = 0.2  # base score
    text = f"{turn.user_query} {turn.assistant_response}".lower()

    # Check keyword triggers
    for pattern in SALIENCE_TRIGGERS:
        if re.search(pattern, text):
            score += 0.4

    # Length heuristic: extremely short generic queries like "hi", "ok" get low score
    if len(turn.user_query.strip()) < 5:
        score -= 0.2

    # Intent heuristic
    if turn.intent_type in ["calendar_create", "task_create"]:
        score += 0.3

    return min(1.0, max(0.0, score))


def turn_to_memory_entry(turn: ConversationTurn, salience_score: float) -> MemoryEntry:
    """Convert a conversation turn to a MemoryEntry."""
    content = f"User said: '{turn.user_query}' | Ultron replied: '{turn.assistant_response}'"
    return MemoryEntry(
        session_id=turn.session_id,
        content=content,
        user_query=turn.user_query,
        assistant_response=turn.assistant_response,
        intent_type=turn.intent_type,
        salience_score=salience_score,
    )
