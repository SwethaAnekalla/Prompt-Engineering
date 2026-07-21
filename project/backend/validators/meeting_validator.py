from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class ActionItemModel(BaseModel):
    model_config = ConfigDict(strict=True)

    task: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    source_chunk: int

class DecisionModel(BaseModel):
    model_config = ConfigDict(strict=True)

    decision: str
    context: str
    source_chunk: int

class RiskModel(BaseModel):
    model_config = ConfigDict(strict=True)

    risk: str
    severity: Literal["low", "medium", "high"]
    source_chunk: int

class DeadlineModel(BaseModel):
    model_config = ConfigDict(strict=True)

    deadline_text: str
    normalized_date: Optional[str] = None
    related_task: Optional[str] = None

class MeetingOutputModel(BaseModel):
    model_config = ConfigDict(strict=True)

    summary: str = ""
    key_topics: List[str] = Field(default_factory=list)
    action_items: List[ActionItemModel] = Field(default_factory=list)
    decisions: List[DecisionModel] = Field(default_factory=list)
    risks: List[RiskModel] = Field(default_factory=list)
    deadlines: List[DeadlineModel] = Field(default_factory=list)

def validate_meeting_output(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a meeting analyzer combined output payload.
    Fills missing optional fields with defaults, enforces strict types, and returns a report.

    Args:
        payload (dict): The combined dictionary payload to validate.

    Returns:
        dict: A dictionary containing:
            - report (dict): { "valid": bool, "errors": list }
            - payload (dict): Corrected or original payload with filled defaults.
    """
    errors = []
    # Make a copy to avoid mutating the original input payload
    validated_payload = payload.copy()

    # Fill in sensible top-level defaults for missing fields
    defaults = {
        "summary": "",
        "key_topics": [],
        "action_items": [],
        "decisions": [],
        "risks": [],
        "deadlines": []
    }
    for key, val in defaults.items():
        if key not in validated_payload:
            validated_payload[key] = val

    try:
        # Validate against strict schemas
        model = MeetingOutputModel.model_validate(validated_payload)
        return {
            "report": {
                "valid": True,
                "errors": []
            },
            "payload": model.model_dump()
        }
    except ValidationError as ve:
        # Format Pydantic errors into human-readable warning messages
        for err in ve.errors():
            loc_path = " -> ".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            errors.append(f"Field '{loc_path}': {msg}")

        return {
            "report": {
                "valid": False,
                "errors": errors
            },
            "payload": validated_payload
        }
