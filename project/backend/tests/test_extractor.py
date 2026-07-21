import pytest
from unittest.mock import patch
from extractor.action_extractor import (
    extract_action_items,
    extract_decisions,
    extract_risks,
    extract_deadlines
)

@pytest.fixture
def mock_env_api_key():
    """Fixture to ensure OPENAI_API_KEY is present for tests."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
        yield

# --- Action Items Tests ---

@patch("extractor.action_extractor.call_llm")
def test_extract_action_items_normal(mock_call_llm, mock_env_api_key):
    """Verify normal action items extraction."""
    mock_response = (
        '{"action_items": ['
        '  {"task": "Implement upload route", "owner": "John", "deadline": "Friday", "priority": "High", "context": "Needs backend work"},'
        '  {"task": "Design frontend UI", "owner": "Alice", "deadline": null, "priority": "Medium", "context": "For upload screen"}'
        ']}'
    )
    mock_call_llm.return_value = mock_response

    result = extract_action_items(["Chunk 1 content"])
    
    assert len(result) == 2
    assert result[0] == {
        "task": "Implement upload route",
        "owner": "John",
        "deadline": "Friday",
        "source_chunk": 0
    }
    assert result[1] == {
        "task": "Design frontend UI",
        "owner": "Alice",
        "deadline": None,
        "source_chunk": 0
    }

@patch("extractor.action_extractor.call_llm")
def test_extract_action_items_empty(mock_call_llm, mock_env_api_key):
    """Verify action item extraction returns empty list if no items are found."""
    mock_response = '{"action_items": []}'
    mock_call_llm.return_value = mock_response

    result = extract_action_items(["Chunk 1"])
    assert result == []

@patch("extractor.action_extractor.call_llm")
@patch("time.sleep", return_value=None)
def test_extract_action_items_malformed_retry_success(mock_sleep, mock_call_llm, mock_env_api_key):
    """Verify retry success on initial malformed JSON for action items."""
    malformed = "not json"
    valid = '{"action_items": [{"task": "Fix tests", "owner": "Bob", "deadline": "today", "priority": "high", "context": "err"}]}'
    mock_call_llm.side_effect = [malformed, valid]

    result = extract_action_items(["Chunk 1"])
    assert len(result) == 1
    assert result[0]["task"] == "Fix tests"
    assert mock_call_llm.call_count == 2

# --- Decisions Tests ---

@patch("extractor.action_extractor.call_llm")
def test_extract_decisions_normal(mock_call_llm, mock_env_api_key):
    """Verify normal decisions extraction."""
    mock_response = (
        '{"decisions": ['
        '  {"decision": "Use FastAPI", "made_by": "Group", "context": "Selected for performance"}'
        ']}'
    )
    mock_call_llm.return_value = mock_response

    result = extract_decisions(["Chunk 1"])
    assert len(result) == 1
    assert result[0] == {
        "decision": "Use FastAPI",
        "context": "Selected for performance",
        "source_chunk": 0
    }

@patch("extractor.action_extractor.call_llm")
def test_extract_decisions_empty(mock_call_llm, mock_env_api_key):
    """Verify decision extraction returns empty list when none exist."""
    mock_response = '{"decisions": []}'
    mock_call_llm.return_value = mock_response
    assert extract_decisions(["Chunk 1"]) == []

@patch("extractor.action_extractor.call_llm")
@patch("time.sleep", return_value=None)
def test_extract_decisions_malformed_retry_failure(mock_sleep, mock_call_llm, mock_env_api_key):
    """Verify extraction failure after persistent malformed response for decisions."""
    mock_call_llm.side_effect = ["malformed 1", "malformed 2"]
    with pytest.raises(RuntimeError, match="Extraction failed"):
        extract_decisions(["Chunk 1"])
    assert mock_call_llm.call_count == 2

# --- Risks Tests ---

@patch("extractor.action_extractor.call_llm")
def test_extract_risks_normal(mock_call_llm, mock_env_api_key):
    """Verify normal risks extraction."""
    mock_response = (
        '{"risks": ['
        '  {"risk": "Database latency", "severity": "High", "mitigation": "Caching", "raised_by": "John", "context": "During peak hours"}'
        ']}'
    )
    mock_call_llm.return_value = mock_response

    result = extract_risks(["Chunk 1"])
    assert len(result) == 1
    assert result[0] == {
        "risk": "Database latency",
        "severity": "high",
        "source_chunk": 0
    }

@patch("extractor.action_extractor.call_llm")
def test_extract_risks_empty(mock_call_llm, mock_env_api_key):
    """Verify risk extraction returns empty list when none exist."""
    mock_response = '{"risks": []}'
    mock_call_llm.return_value = mock_response
    assert extract_risks(["Chunk 1"]) == []

# --- Deadlines Tests ---

@patch("extractor.action_extractor.call_llm")
def test_extract_deadlines_normal_with_date(mock_call_llm, mock_env_api_key):
    """Verify deadlines extraction and date normalization when meeting date is provided."""
    mock_response = (
        '{"deadlines": ['
        '  {"deadline_text": "next Friday", "normalized_date": "2026-07-24", "related_task": "Scaffold completion"}'
        ']}'
    )
    mock_call_llm.return_value = mock_response

    result = extract_deadlines(["Chunk 1"], meeting_date="2026-07-17")
    
    assert len(result) == 1
    assert result[0] == {
        "deadline_text": "next Friday",
        "normalized_date": "2026-07-24",
        "related_task": "Scaffold completion"
    }

@patch("extractor.action_extractor.call_llm")
def test_extract_deadlines_normal_without_date(mock_call_llm, mock_env_api_key):
    """Verify deadlines extraction keeps normalized_date null when meeting date is unknown."""
    mock_response = (
        '{"deadlines": ['
        '  {"deadline_text": "end of month", "normalized_date": null, "related_task": "Final presentation"}'
        ']}'
    )
    mock_call_llm.return_value = mock_response

    result = extract_deadlines(["Chunk 1"], meeting_date=None)
    
    assert len(result) == 1
    assert result[0] == {
        "deadline_text": "end of month",
        "normalized_date": None,
        "related_task": "Final presentation"
    }

@patch("extractor.action_extractor.call_llm")
def test_extract_deadlines_empty(mock_call_llm, mock_env_api_key):
    """Verify deadline extraction returns empty list when none exist."""
    mock_response = '{"deadlines": []}'
    mock_call_llm.return_value = mock_response
    assert extract_deadlines(["Chunk 1"]) == []
