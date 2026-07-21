import pytest
from validators.meeting_validator import validate_meeting_output

def test_validate_fully_valid_payload():
    """Verify that a correct payload passes validation with no errors."""
    payload = {
        "summary": "The team successfully completed scaffolding and upload features.",
        "key_topics": ["Scaffolding", "Upload module", "Testing"],
        "action_items": [
            {
                "task": "Create validation models",
                "owner": "Developer",
                "deadline": "End of week",
                "source_chunk": 0
            }
        ],
        "decisions": [
            {
                "decision": "Use Pydantic strict mode",
                "context": "Prevents silent type coercion during API data sync",
                "source_chunk": 0
            }
        ],
        "risks": [
            {
                "risk": "API rate limits during tests",
                "severity": "medium",
                "source_chunk": 0
            }
        ],
        "deadlines": [
            {
                "deadline_text": "Friday afternoon",
                "normalized_date": "2026-07-17",
                "related_task": "Create validation models"
            }
        ]
    }
    
    result = validate_meeting_output(payload)
    
    assert result["report"]["valid"] is True
    assert len(result["report"]["errors"]) == 0
    assert result["payload"]["summary"] == payload["summary"]
    assert len(result["payload"]["action_items"]) == 1
    assert result["payload"]["action_items"][0]["owner"] == "Developer"

def test_validate_wrong_types_rejection():
    """Verify that wrong types are rejected and flagged instead of silently coerced."""
    payload = {
        "summary": 9999,  # Int instead of String (should fail)
        "key_topics": ["Validation"],
        "action_items": [
            {
                "task": "Fix types",
                "owner": "Bob",
                "deadline": None,
                "source_chunk": "first"  # String instead of Int (should fail)
            }
        ],
        "risks": [
            {
                "risk": "Invalid severity",
                "severity": "extremely_high",  # Wrong literal value (should fail)
                "source_chunk": 0
            }
        ]
    }
    
    result = validate_meeting_output(payload)
    
    assert result["report"]["valid"] is False
    assert len(result["report"]["errors"]) > 0
    
    # Assert specific fields were caught in errors list
    errors_str = " ".join(result["report"]["errors"])
    assert "summary" in errors_str
    assert "source_chunk" in errors_str
    assert "severity" in errors_str

def test_validate_missing_optional_fields_defaults():
    """Verify that missing optional fields are filled with defaults rather than failing."""
    # Payload is missing: key_topics, action_items, decisions, risks, deadlines
    payload = {
        "summary": "This is a basic sync meeting."
    }
    
    result = validate_meeting_output(payload)
    
    assert result["report"]["valid"] is True
    assert len(result["report"]["errors"]) == 0
    
    # Verify defaults are filled in corrected payload
    corrected = result["payload"]
    assert corrected["summary"] == "This is a basic sync meeting."
    assert corrected["key_topics"] == []
    assert corrected["action_items"] == []
    assert corrected["decisions"] == []
    assert corrected["risks"] == []
    assert corrected["deadlines"] == []
