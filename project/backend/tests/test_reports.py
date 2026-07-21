import os
import json
import pytest
from datetime import datetime
from reports.report_generator import generate_markdown_report, generate_pdf_report

class MockDBMeeting:
    def __init__(self):
        self.id = "test-meeting-123"
        self.filename = "test_transcript.txt"
        self.upload_timestamp = datetime.now()
        self.meeting_date = "2026-07-14"
        self.raw_summary = "This is a test summary."
        self.key_topics = json.dumps(["Testing", "Reports"])
        
        # Lists of mock objects
        self.action_items = [MockAI()]
        self.decisions = [MockDecision()]
        self.risks = []  # Empty to test missing optional data handling
        self.deadlines = [MockDeadline()]

class MockAI:
    task = "Write unit tests"
    owner = "Dev"
    deadline = "Tomorrow"
    source_chunk = 1

class MockDecision:
    decision = "Use fpdf2"
    context = "We need pure python"
    source_chunk = 1

class MockDeadline:
    deadline_text = "End of week"
    normalized_date = "2026-07-17"
    related_task = "Release feature"

def test_generate_markdown_report():
    meeting = MockDBMeeting()
    
    filepath = generate_markdown_report(meeting)
    
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "Meeting Minutes Report" in content
    assert "This is a test summary." in content
    assert "No risks identified." in content
    assert "Use fpdf2" in content
    
    # Clean up
    os.remove(filepath)

def test_generate_pdf_report():
    meeting = MockDBMeeting()
    
    filepath = generate_pdf_report(meeting)
    
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0
    
    # Read binary
    with open(filepath, "rb") as f:
        content = f.read()
    
    # PDF magic number
    assert content.startswith(b"%PDF-")
    
    # Clean up
    os.remove(filepath)
