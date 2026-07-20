import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import Meeting, ActionItem, Decision, Risk, Deadline

def save_meeting_result(
    db: Session,
    meeting_id: str,
    validated_payload: Dict[str, Any],
    filename: str = "unknown",
    upload_timestamp: Optional[datetime] = None,
    meeting_date: Optional[str] = None
) -> Meeting:
    """
    Saves a validated meeting analysis payload (summary, key_topics, action items,
    decisions, risks, deadlines) to the database.

    Args:
        db (Session): Database session.
        meeting_id (str): Unique file ID/UUID.
        validated_payload (dict): Output dictionary validated by the validator module.
        filename (str): The name of the file uploaded.
        upload_timestamp (datetime, optional): Timestamp of upload. Defaults to UTC now.
        meeting_date (str, optional): Target meeting date.

    Returns:
        Meeting: The created Meeting database record.
    """
    if upload_timestamp is None:
        upload_timestamp = datetime.now(timezone.utc)

    # Convert key_topics list to a serialized JSON string
    key_topics_json = json.dumps(validated_payload.get("key_topics", []))

    # Create and add the primary Meeting record
    db_meeting = Meeting(
        id=meeting_id,
        filename=filename,
        upload_timestamp=upload_timestamp,
        meeting_date=meeting_date,
        raw_summary=validated_payload.get("summary", ""),
        key_topics=key_topics_json
    )
    db.add(db_meeting)

    # Add Action Items
    for item in validated_payload.get("action_items", []):
        db_action = ActionItem(
            meeting_id=meeting_id,
            task=item["task"],
            owner=item.get("owner"),
            deadline=item.get("deadline"),
            source_chunk=item["source_chunk"]
        )
        db.add(db_action)

    # Add Decisions
    for item in validated_payload.get("decisions", []):
        db_decision = Decision(
            meeting_id=meeting_id,
            decision=item["decision"],
            context=item["context"],
            source_chunk=item["source_chunk"]
        )
        db.add(db_decision)

    # Add Risks
    for item in validated_payload.get("risks", []):
        db_risk = Risk(
            meeting_id=meeting_id,
            risk=item["risk"],
            severity=item["severity"],
            source_chunk=item["source_chunk"]
        )
        db.add(db_risk)

    # Add Deadlines
    for item in validated_payload.get("deadlines", []):
        db_deadline = Deadline(
            meeting_id=meeting_id,
            deadline_text=item["deadline_text"],
            normalized_date=item.get("normalized_date"),
            related_task=item.get("related_task")
        )
        db.add(db_deadline)

    db.commit()
    db.refresh(db_meeting)
    return db_meeting

def get_meeting_by_id(db: Session, meeting_id: str) -> Optional[Meeting]:
    """
    Retrieve a meeting record and its related entities by its ID.
    """
    return db.query(Meeting).filter(Meeting.id == meeting_id).first()

def search_meetings(db: Session, query: str) -> List[Meeting]:
    """
    Searches for meeting records across:
      - Meeting raw summaries
      - Meeting key topics (JSON array string representation)
      - Associated Action Item tasks
    
    Returns:
        list: Distinct list of matching Meeting records.
    """
    if not query or not query.strip():
        return []

    search_filter = f"%{query.strip()}%"

    return db.query(Meeting).outerjoin(ActionItem).filter(
        or_(
            Meeting.raw_summary.like(search_filter),
            Meeting.key_topics.like(search_filter),
            ActionItem.task.like(search_filter)
        )
    ).distinct().all()
