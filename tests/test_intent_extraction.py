"""
Integration tests for intent extraction pipeline (Stage 3).

Tests LLM function-calling returns valid Intent schema,
confidence thresholds, and error handling.
"""
import json
import pytest
from pathlib import Path
from datetime import datetime

from jarvis.stages.intent_extraction import (
    handle_intent_extraction,
    _parse_and_validate_intent,
    _requires_confirmation,
    MIN_INTENT_CONFIDENCE,
)
from jarvis.services.llm import extract_intent, LLMExtractionError
from jarvis.state.states import StateData, PipelineState
from jarvis.schemas.pipeline import PipelineRun
from jarvis.schemas.intent import (
    Intent,
    IntentType,
    WeatherIntent,
    CalendarCreateIntent,
    CalendarListIntent,
    TaskCreateIntent,
    TaskListIntent,
    UnknownIntent,
)
from jarvis.stages.intent_extraction import RetryableError, NonRetryableError


# Load test fixtures
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_transcripts.json"
with open(FIXTURE_PATH) as f:
    TRANSCRIPT_FIXTURES = json.load(f)


def get_all_transcripts():
    """Flatten all transcript test cases."""
    all_cases = []
    for category, cases in TRANSCRIPT_FIXTURES.items():
        for case in cases:
            case["category"] = category
            all_cases.append(case)
    return all_cases


@pytest.fixture
def state_with_transcript():
    """Create a state with a transcript for testing."""
    def _create(transcript: str):
        run = PipelineRun(session_id="test-session", user_id="test-user")
        state = StateData(run=run)
        # Mock transcription result
        from jarvis.schemas.api import TranscriptionResponse
        state.transcription = TranscriptionResponse(
            text=transcript,
            confidence=0.9,
            language="en",
            duration_ms=1000,
        )
        state.current_state = PipelineState.EXTRACTING_INTENT
        return state
    return _create


class TestIntentSchemaValidation:
    """Test that intent schemas validate correctly."""

    def test_weather_intent_valid(self):
        """Test valid weather intent."""
        intent = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            units="metric",
            confidence=0.9,
        )
        assert intent.type == IntentType.WEATHER
        assert intent.location == "London"
        assert intent.confidence == 0.9

    def test_calendar_create_intent_valid(self):
        """Test valid calendar create intent."""
        intent = CalendarCreateIntent(
            type=IntentType.CALENDAR_CREATE,
            title="Meeting",
            start_time=datetime(2024, 1, 15, 14, 0),
            end_time=datetime(2024, 1, 15, 15, 0),
            confidence=0.8,
        )
        assert intent.type == IntentType.CALENDAR_CREATE
        assert intent.title == "Meeting"

    def test_calendar_list_intent_valid(self):
        """Test valid calendar list intent."""
        intent = CalendarListIntent(
            type=IntentType.CALENDAR_LIST,
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 22),
            confidence=0.8,
        )
        assert intent.type == IntentType.CALENDAR_LIST

    def test_task_create_intent_valid(self):
        """Test valid task create intent."""
        intent = TaskCreateIntent(
            type=IntentType.TASK_CREATE,
            title="Buy groceries",
            priority="high",
            confidence=0.8,
        )
        assert intent.type == IntentType.TASK_CREATE
        assert intent.priority == "high"

    def test_task_list_intent_valid(self):
        """Test valid task list intent."""
        intent = TaskListIntent(
            type=IntentType.TASK_LIST,
            status="pending",
            confidence=0.8,
        )
        assert intent.type == IntentType.TASK_LIST
        assert intent.status == "pending"

    def test_unknown_intent_valid(self):
        """Test valid unknown intent."""
        intent = UnknownIntent(
            type=IntentType.UNKNOWN,
            raw_text="Hello there",
            confidence=0.3,
        )
        assert intent.type == IntentType.UNKNOWN
        assert intent.raw_text == "Hello there"

    def test_confidence_bounds(self):
        """Test confidence must be 0-1."""
        with pytest.raises(ValueError):
            WeatherIntent(
                type=IntentType.WEATHER,
                location="London",
                confidence=1.5,
            )
        with pytest.raises(ValueError):
            WeatherIntent(
                type=IntentType.WEATHER,
                location="London",
                confidence=-0.1,
            )

    def test_discriminated_union_validation(self):
        """Test Pydantic discriminated union works."""
        from pydantic import TypeAdapter
        from jarvis.schemas.intent import Intent
        
        # Use TypeAdapter for Union validation
        adapter = TypeAdapter(Intent)
        
        # Valid weather intent
        data = {"type": "weather", "location": "London", "confidence": 0.9}
        intent = adapter.validate_python(data)
        assert isinstance(intent, WeatherIntent)

        # Valid unknown intent
        data = {"type": "unknown", "raw_text": "hello", "confidence": 0.3}
        intent = adapter.validate_python(data)
        assert isinstance(intent, UnknownIntent)

        # Invalid type should fail
        with pytest.raises(ValueError):
            adapter.validate_python({"type": "invalid", "confidence": 0.5})


class TestParseAndValidateIntent:
    """Test _parse_and_validate_intent function."""

    def test_valid_weather_json(self):
        """Test parsing valid weather intent JSON."""
        json_data = {
            "type": "weather",
            "location": "London",
            "units": "metric",
            "confidence": 0.9,
        }
        intent = _parse_and_validate_intent(json_data)
        assert isinstance(intent, WeatherIntent)
        assert intent.location == "London"

    def test_valid_calendar_create_json(self):
        """Test parsing valid calendar create intent JSON."""
        json_data = {
            "type": "calendar_create",
            "title": "Meeting",
            "start_time": "2024-01-15T14:00:00",
            "end_time": "2024-01-15T15:00:00",
            "confidence": 0.8,
        }
        intent = _parse_and_validate_intent(json_data)
        assert isinstance(intent, CalendarCreateIntent)
        assert intent.title == "Meeting"

    def test_invalid_json_raises(self):
        """Test invalid JSON raises ValueError."""
        # Missing required field
        json_data = {"type": "weather", "confidence": 0.9}
        with pytest.raises(ValueError):
            _parse_and_validate_intent(json_data)

    def test_unknown_intent_json(self):
        """Test parsing unknown intent JSON."""
        json_data = {
            "type": "unknown",
            "raw_text": "hello world",
            "confidence": 0.3,
        }
        intent = _parse_and_validate_intent(json_data)
        assert isinstance(intent, UnknownIntent)
        assert intent.raw_text == "hello world"


class TestRequiresConfirmation:
    """Test _requires_confirmation function."""

    def test_calendar_create_requires_confirmation(self):
        """Calendar create should require confirmation."""
        intent = CalendarCreateIntent(
            type=IntentType.CALENDAR_CREATE,
            title="Meeting",
            start_time=datetime(2024, 1, 15, 14, 0),
            end_time=datetime(2024, 1, 15, 15, 0),
            confidence=0.8,
        )
        assert _requires_confirmation(intent) is True

    def test_task_create_requires_confirmation(self):
        """Task create should require confirmation."""
        intent = TaskCreateIntent(
            type=IntentType.TASK_CREATE,
            title="Buy groceries",
            confidence=0.8,
        )
        assert _requires_confirmation(intent) is True

    def test_weather_no_confirmation(self):
        """Weather should not require confirmation."""
        intent = WeatherIntent(
            type=IntentType.WEATHER,
            location="London",
            confidence=0.9,
        )
        assert _requires_confirmation(intent) is False

    def test_calendar_list_no_confirmation(self):
        """Calendar list should not require confirmation."""
        intent = CalendarListIntent(
            type=IntentType.CALENDAR_LIST,
            confidence=0.8,
        )
        assert _requires_confirmation(intent) is False

    def test_task_list_no_confirmation(self):
        """Task list should not require confirmation."""
        intent = TaskListIntent(
            type=IntentType.TASK_LIST,
            confidence=0.8,
        )
        assert _requires_confirmation(intent) is False

    def test_unknown_no_confirmation(self):
        """Unknown should not require confirmation."""
        intent = UnknownIntent(
            type=IntentType.UNKNOWN,
            raw_text="hello",
            confidence=0.3,
        )
        assert _requires_confirmation(intent) is False


class TestIntentExtractionStage:
    """Test handle_intent_extraction stage handler."""

    @pytest.mark.asyncio
    async def test_no_transcription_fails(self):
        """Test missing transcription fails appropriately."""
        run = PipelineRun(session_id="test", user_id="test")
        state = StateData(run=run)
        state.current_state = PipelineState.EXTRACTING_INTENT
        # No transcription set

        with pytest.raises(NonRetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert state.current_state == PipelineState.FAILED
        assert "No transcription available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_transcription_fails(self):
        """Test empty transcription fails."""
        run = PipelineRun(session_id="test", user_id="test")
        state = StateData(run=run)
        state.current_state = PipelineState.EXTRACTING_INTENT
        from jarvis.schemas.api import TranscriptionResponse
        state.transcription = TranscriptionResponse(
            text="",
            confidence=0.9,
            language="en",
            duration_ms=1000,
        )

        with pytest.raises(NonRetryableError):
            await handle_intent_extraction(state)

        assert state.current_state == PipelineState.FAILED


class TestConfidenceThreshold:
    """Test confidence threshold behavior."""

    def test_min_confidence_constant(self):
        """Test MIN_INTENT_CONFIDENCE is set correctly."""
        assert MIN_INTENT_CONFIDENCE == 0.5

    @pytest.mark.asyncio
    async def test_low_confidence_fails(self, state_with_transcript, monkeypatch):
        """Test intent with confidence below threshold fails."""
        state = state_with_transcript("What's the weather?")

        # Mock extract_intent to return low confidence
        async def mock_extract_intent(*args, **kwargs):
            from jarvis.services.llm import LLMExtractionResult
            return LLMExtractionResult(
                intent_json={
                    "type": "weather",
                    "location": "London",
                    "confidence": 0.3,  # Below threshold
                },
                raw_output="{}",
                latency_ms=100,
            )

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(NonRetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert state.current_state == PipelineState.FAILED
        assert "INTENT_LOW_CONFIDENCE" in str(exc_info.value)
        assert "0.30" in str(exc_info.value)
        assert "0.5" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_high_confidence_succeeds(self, state_with_transcript, monkeypatch):
        """Test intent with confidence above threshold succeeds."""
        state = state_with_transcript("What's the weather in London?")

        async def mock_extract_intent(*args, **kwargs):
            from jarvis.services.llm import LLMExtractionResult
            return LLMExtractionResult(
                intent_json={
                    "type": "weather",
                    "location": "London",
                    "confidence": 0.9,
                },
                raw_output="{}",
                latency_ms=100,
            )

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        result = await handle_intent_extraction(state)

        assert result.current_state == PipelineState.CONFIRMING_INTENT
        assert result.intent is not None
        assert result.intent.type == IntentType.WEATHER
        assert result.intent.confidence == 0.9
        assert result.requires_confirmation is False


class TestLLMErrorHandling:
    """Test LLM error handling in intent extraction."""

    @pytest.mark.asyncio
    async def test_llm_timeout_retries(self, state_with_transcript, monkeypatch):
        """Test LLM timeout raises RetryableError."""
        state = state_with_transcript("What's the weather?")

        async def mock_extract_intent(*args, **kwargs):
            raise LLMExtractionError("Timeout", "timeout")

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(RetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert "LLM transient error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_llm_rate_limit_retries(self, state_with_transcript, monkeypatch):
        """Test LLM rate limit raises RetryableError."""
        state = state_with_transcript("What's the weather?")

        async def mock_extract_intent(*args, **kwargs):
            raise LLMExtractionError("Rate limited", "rate_limit")

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(RetryableError):
            await handle_intent_extraction(state)

    @pytest.mark.asyncio
    async def test_llm_auth_fails_permanently(self, state_with_transcript, monkeypatch):
        """Test LLM auth error raises NonRetryableError."""
        state = state_with_transcript("What's the weather?")

        async def mock_extract_intent(*args, **kwargs):
            raise LLMExtractionError("Auth failed", "auth")

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(NonRetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert "LLM permanent error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_json_fails(self, state_with_transcript, monkeypatch):
        """Test malformed JSON from LLM fails."""
        state = state_with_transcript("What's the weather?")

        async def mock_extract_intent(*args, **kwargs):
            from jarvis.services.llm import LLMExtractionResult
            return LLMExtractionResult(
                intent_json="not a dict",  # Invalid - should be dict
                raw_output="{}",
                latency_ms=100,
            )

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(NonRetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert "INTENT_MALFORMED_JSON" in str(exc_info.value) or "INTENT_SCHEMA_VIOLATION" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_schema_violation_fails(self, state_with_transcript, monkeypatch):
        """Test schema violation from LLM fails."""
        state = state_with_transcript("What's the weather?")

        async def mock_extract_intent(*args, **kwargs):
            from jarvis.services.llm import LLMExtractionResult
            return LLMExtractionResult(
                intent_json={
                    "type": "weather",
                    # Missing required 'location' field
                    "confidence": 0.9,
                },
                raw_output="{}",
                latency_ms=100,
            )

        monkeypatch.setattr("jarvis.stages.intent_extraction.extract_intent", mock_extract_intent)

        with pytest.raises(NonRetryableError) as exc_info:
            await handle_intent_extraction(state)

        assert "INTENT_SCHEMA_VIOLATION" in str(exc_info.value)


class TestIntentExtractionIntegration:
    """Integration tests using real LLM (requires API keys)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_llm_weather_intent(self):
        """Test real LLM extracts weather intent correctly."""
        # This test requires GROQ_API_KEY or ANTHROPIC_API_KEY
        transcript = "What's the weather like in London today?"
        
        try:
            result = await extract_intent(transcript, provider="groq")
        except LLMExtractionError as e:
            if e.error_type == "auth":
                pytest.skip("Groq API key not configured")
            raise

        # Validate result structure
        assert "intent_json" in result.__dict__
        assert "raw_output" in result.__dict__
        assert "latency_ms" in result.__dict__

        # Parse and validate intent
        intent = _parse_and_validate_intent(result.intent_json)
        
        # Should be weather intent
        assert isinstance(intent, WeatherIntent)
        assert intent.type == IntentType.WEATHER
        assert intent.confidence >= 0.0
        assert intent.confidence <= 1.0
        assert "London" in intent.location or "london" in intent.location.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.parametrize("case", get_all_transcripts())
    async def test_real_llm_all_transcripts(self, case):
        """Test real LLM against all transcript fixtures."""
        transcript = case["transcript"]
        expected_intent = case["expected_intent"]
        
        try:
            result = await extract_intent(transcript, provider="groq")
        except LLMExtractionError as e:
            if e.error_type == "auth":
                pytest.skip("Groq API key not configured")
            raise

        intent = _parse_and_validate_intent(result.intent_json)
        
        # Check intent type matches expected
        assert intent.type.value == expected_intent, \
            f"Transcript: '{transcript}' - Expected {expected_intent}, got {intent.type.value}"

        # Check confidence bounds
        if "expected_confidence_min" in case:
            assert intent.confidence >= case["expected_confidence_min"], \
                f"Transcript: '{transcript}' - Confidence {intent.confidence} below minimum {case['expected_confidence_min']}"
        
        if "expected_confidence_max" in case:
            assert intent.confidence <= case["expected_confidence_max"], \
                f"Transcript: '{transcript}' - Confidence {intent.confidence} above maximum {case['expected_confidence_max']}"

        # For weather, check location extraction
        if expected_intent == "weather" and "expected_location" in case:
            expected_loc = case["expected_location"].lower()
            actual_loc = intent.location.lower()
            assert expected_loc in actual_loc or actual_loc in expected_loc, \
                f"Transcript: '{transcript}' - Expected location '{expected_loc}', got '{actual_loc}'"


class TestFullPipelineIntentExtraction:
    """Test full pipeline through intent extraction stage."""

    @pytest.mark.asyncio
    async def test_audio_to_intent_pipeline_mock(self, monkeypatch):
        """Test complete audio -> transcription -> intent pipeline with mocks."""
        import jarvis.stages.audio_input as audio_input_module
        import jarvis.stages.transcription as transcription_module
        import jarvis.stages.intent_extraction as intent_extraction_module
        from jarvis.schemas.api import AudioInputRequest, TranscriptionResponse
        from jarvis.schemas.pipeline import PipelineRun
        from jarvis.state.states import StateData, PipelineState
        from jarvis.schemas.intent import WeatherIntent, IntentType
        import base64

        # Create initial state with fake audio
        run = PipelineRun(session_id="test", user_id="test")
        state = StateData(run=run)
        fake_audio = base64.b64encode(b"fake wav data").decode()
        state._audio_request = AudioInputRequest(
            audio_base64=fake_audio,
            session_id="test",
            user_id="test",
        )

        # Mock audio input
        async def mock_audio_input(s):
            s.current_state = PipelineState.TRANSCRIBING
            s.audio_bytes = b"fake wav"
            s.audio_format = "wav"
            s.audio_duration_ms = 1000
            return s

        # Mock transcription
        async def mock_transcription(s):
            s.current_state = PipelineState.EXTRACTING_INTENT
            s.transcription = TranscriptionResponse(
                text="What's the weather in London?",
                confidence=0.9,
                language="en",
                duration_ms=1000,
            )
            return s

        # Mock intent extraction
        async def mock_intent_extraction(s):
            s.current_state = PipelineState.CONFIRMING_INTENT
            s.intent = WeatherIntent(
                type=IntentType.WEATHER,
                location="London",
                confidence=0.9,
            )
            s.requires_confirmation = False
            return s

        monkeypatch.setattr(audio_input_module, "handle_audio_input", mock_audio_input)
        monkeypatch.setattr(transcription_module, "handle_transcription", mock_transcription)
        monkeypatch.setattr(intent_extraction_module, "handle_intent_extraction", mock_intent_extraction)

        # Run pipeline
        state = await audio_input_module.handle_audio_input(state)
        assert state.current_state == PipelineState.TRANSCRIBING

        state = await transcription_module.handle_transcription(state)
        assert state.current_state == PipelineState.EXTRACTING_INTENT

        state = await intent_extraction_module.handle_intent_extraction(state)
        assert state.current_state == PipelineState.CONFIRMING_INTENT
        assert state.intent is not None
        assert state.intent.type == IntentType.WEATHER
