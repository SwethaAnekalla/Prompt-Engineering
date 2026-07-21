import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.connection import Base
from database.crud import save_meeting_result, get_meeting_by_id, search_meetings
from database.models import Meeting

@pytest.fixture(name="db_session")
def db_session_fixture():
    """Fixture to set up an in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_save_and_retrieve_meeting(db_session):
    """Verify that a meeting and all its related entities are correctly saved and retrieved."""
    meeting_id = "test-uuid-12345"
    payload = {
        "summary": "This meeting covered database migration plans.",
        "key_topics": ["Database", "Migration"],
        "action_items": [
            {"task": "Write SQL scripts", "owner": "John", "deadline": "Monday", "source_chunk": 0}
        ],
        "decisions": [
            {"decision": "Use SQLite locally", "context": "Easier dev environment", "source_chunk": 0}
        ],
        "risks": [
            {"risk": "Data loss during migration", "severity": "high", "source_chunk": 0}
        ],
        "deadlines": [
            {"deadline_text": "Next week", "normalized_date": "2026-07-21", "related_task": "Write SQL scripts"}
        ]
    }

    # Save
    meeting_date = "2026-07-14"
    filename = "meeting_transcript.txt"
    timestamp = datetime.now(timezone.utc)
    
    saved_meeting = save_meeting_result(
        db=db_session,
        meeting_id=meeting_id,
        validated_payload=payload,
        filename=filename,
        upload_timestamp=timestamp,
        meeting_date=meeting_date
    )

    assert saved_meeting.id == meeting_id
    assert saved_meeting.filename == filename

    # Retrieve and check
    retrieved = get_meeting_by_id(db_session, meeting_id)
    assert retrieved is not None
    assert retrieved.id == meeting_id
    assert retrieved.filename == filename
    assert retrieved.raw_summary == "This meeting covered database migration plans."
    assert "Database" in retrieved.key_topics
    
    # Check related entities
    assert len(retrieved.action_items) == 1
    assert retrieved.action_items[0].task == "Write SQL scripts"
    assert retrieved.action_items[0].owner == "John"
    
    assert len(retrieved.decisions) == 1
    assert retrieved.decisions[0].decision == "Use SQLite locally"
    
    assert len(retrieved.risks) == 1
    assert retrieved.risks[0].risk == "Data loss during migration"
    assert retrieved.risks[0].severity == "high"
    
    assert len(retrieved.deadlines) == 1
    assert retrieved.deadlines[0].deadline_text == "Next week"
    assert retrieved.deadlines[0].normalized_date == "2026-07-21"

def test_search_meetings_matches(db_session):
    """Verify that search returns correct matches across summaries, topics, and action items."""
    # Setup meeting 1
    save_meeting_result(
        db=db_session,
        meeting_id="m1",
        validated_payload={
            "summary": "Discussed the frontend UI layout.",
            "key_topics": ["frontend", "UI"],
            "action_items": [{"task": "Refactor CSS", "owner": None, "deadline": None, "source_chunk": 0}],
            "decisions": [], "risks": [], "deadlines": []
        },
        filename="f1.txt"
    )

    # Setup meeting 2
    save_meeting_result(
        db=db_session,
        meeting_id="m2",
        validated_payload={
            "summary": "Backend route definition sync.",
            "key_topics": ["backend", "API"],
            "action_items": [{"task": "Define upload schema", "owner": None, "deadline": None, "source_chunk": 0}],
            "decisions": [], "risks": [], "deadlines": []
        },
        filename="f2.txt"
    )

    # 1. Search in summaries
    results = search_meetings(db_session, "frontend")
    assert len(results) == 1
    assert results[0].id == "m1"

    # 2. Search in key topics
    results = search_meetings(db_session, "API")
    assert len(results) == 1
    assert results[0].id == "m2"

    # 3. Search in action item tasks
    results = search_meetings(db_session, "Refactor")
    assert len(results) == 1
    assert results[0].id == "m1"

    # 4. Search that matches multiple (case-insensitive checks depend on collation, SQLite is case-sensitive by default for LIKE unless configured, but our test queries match case)
    results = search_meetings(db_session, "Discussed")
    assert len(results) == 1
    assert results[0].id == "m1"

def test_search_meetings_no_matches_and_empty_query(db_session):
    """Verify that search returns empty lists when no records match or query is empty."""
    # Setup meeting
    save_meeting_result(
        db=db_session,
        meeting_id="m1",
        validated_payload={
            "summary": "Standard sync.",
            "key_topics": ["sync"],
            "action_items": [], "decisions": [], "risks": [], "deadlines": []
        },
        filename="f1.txt"
    )

    # 1. Search for non-existent keyword
    assert search_meetings(db_session, "missing") == []

    # 2. Search with empty query
    assert search_meetings(db_session, "") == []
    assert search_meetings(db_session, "   ") == []
