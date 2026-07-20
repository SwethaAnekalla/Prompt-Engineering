import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.main import app, UPLOAD_DIR

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_uploads_directory():
    """Fixture to clean the uploads directory before and after each test."""
    # Ensure UPLOAD_DIR exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Keep track of existing files to avoid deleting anything we shouldn't
    initial_files = os.listdir(UPLOAD_DIR)
    
    yield
    
    # Clean up files created during testing
    for file in os.listdir(UPLOAD_DIR):
        if file not in initial_files:
            file_path = os.path.join(UPLOAD_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

def test_health_endpoint():
    """Verify that the health check endpoint returns 200 and correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_upload_valid_txt_file():
    """Verify that a valid .txt file is successfully uploaded and saved."""
    file_content = b"This is a valid meeting transcript."
    files = {"file": ("meeting_transcript.txt", file_content, "text/plain")}
    
    response = client.post("/api/upload/transcript", files=files)
    assert response.status_code == 201
    
    data = response.json()
    assert data["status"] == "success"
    assert "file_id" in data
    assert "upload_timestamp" in data
    assert data["original_filename"] == "meeting_transcript.txt"
    assert data["filename"].endswith(".txt")
    
    # Check if file actually exists on disk
    saved_file_path = os.path.join(UPLOAD_DIR, data["filename"])
    assert os.path.exists(saved_file_path)
    with open(saved_file_path, "rb") as f:
        assert f.read() == file_content

def test_upload_valid_docx_file():
    """Verify that a valid .docx file is successfully uploaded and saved."""
    file_content = b"Dummy docx binary content."
    files = {"file": ("meeting.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    
    response = client.post("/api/upload/transcript", files=files)
    assert response.status_code == 201
    
    data = response.json()
    assert data["status"] == "success"
    assert data["original_filename"] == "meeting.docx"
    assert data["filename"].endswith(".docx")
    
    # Check if file actually exists on disk
    saved_file_path = os.path.join(UPLOAD_DIR, data["filename"])
    assert os.path.exists(saved_file_path)

def test_upload_invalid_file_extension():
    """Verify that uploads with invalid file extensions (e.g., .pdf) are rejected."""
    file_content = b"PDF content..."
    files = {"file": ("meeting.pdf", file_content, "application/pdf")}
    
    response = client.post("/api/upload/transcript", files=files)
    assert response.status_code == 400
    
    data = response.json()
    assert "Unsupported file type" in data["detail"]

def test_upload_empty_file():
    """Verify that uploading an empty file returns a 400 'Empty transcript' error."""
    files = {"file": ("empty.txt", b"", "text/plain")}
    
    response = client.post("/api/upload/transcript", files=files)
    assert response.status_code == 400
    
    data = response.json()
    assert data["detail"] == "Empty transcript"
