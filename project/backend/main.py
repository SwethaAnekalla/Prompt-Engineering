import logging
import time
import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()


# Import our modules
from database.connection import get_db, engine, Base
from database import models, crud
from parsers.transcript_parser import parse_transcript
from summarizer.summary_generator import generate_summary
from extractor.action_extractor import (
    extract_action_items,
    extract_decisions,
    extract_risks,
    extract_deadlines
)
from validators.meeting_validator import validate_meeting_output
from reports.report_generator import generate_report

# Create tables
models.Base.metadata.create_all(bind=engine)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api")

app = FastAPI(
    title="AI Meeting Minutes Generator & Action Item Extractor",
    description="API for parsing, summarizing, extracting action items, and generating reports from meeting transcripts.",
    version="0.1.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Meeting Minutes Generator API",
        "version": "0.1.0"
    }

@app.post("/api/upload/transcript", status_code=status.HTTP_201_CREATED, tags=["Upload"])
async def upload_transcript(file: UploadFile = File(...)):
    filename = file.filename
    logger.info(f"Upload attempt for file: '{filename}'")

    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in [".txt", ".docx"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{file_ext}'")

    contents = await file.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty transcript")

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    file_id = str(uuid.uuid4())
    unique_filename = f"{timestamp}_{file_id}{file_ext}"
    
    dest_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(dest_path, "wb") as f:
        f.write(contents)

    return {
        "file_id": file_id,
        "filename": unique_filename,
        "original_filename": filename,
        "upload_timestamp": now.isoformat(),
        "status": "success"
    }

@app.post("/api/process/{file_id}", tags=["Process"])
async def process_transcript(file_id: str, db: Session = Depends(get_db)):
    # Find file
    matched_file = None
    for f in os.listdir(UPLOAD_DIR):
        if file_id in f:
            matched_file = f
            break
            
    if not matched_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    filepath = os.path.join(UPLOAD_DIR, matched_file)
    file_ext = os.path.splitext(matched_file)[1].lower()
    
    with open(filepath, "rb") as f:
        contents = f.read()
        
    logger.info(f"Starting parsing for {matched_file}")
    try:
        parsed = parse_transcript(contents, file_ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    chunks = parsed["chunks"]
    if not chunks:
        raise HTTPException(status_code=400, detail="Transcript is empty after parsing")
        
    logger.info(f"Processing {len(chunks)} chunks for file_id {file_id}")
    
   # LLM processing — small delay between calls to avoid bursting Gemini's rate limit
    LLM_CALL_SPACING_SECONDS = 3

    logger.info("Starting LLM map-reduce summary generation")
    summary_data = generate_summary(chunks)
    time.sleep(LLM_CALL_SPACING_SECONDS)

    logger.info("Starting LLM action item extraction")
    action_items = extract_action_items(chunks)
    time.sleep(LLM_CALL_SPACING_SECONDS)

    logger.info("Starting LLM decisions extraction")
    decisions = extract_decisions(chunks)
    time.sleep(LLM_CALL_SPACING_SECONDS)

    logger.info("Starting LLM risks extraction")
    risks = extract_risks(chunks)
    time.sleep(LLM_CALL_SPACING_SECONDS)

    logger.info("Starting LLM deadlines extraction")
    deadlines = extract_deadlines(chunks)
    
    payload = {
        "summary": summary_data.get("summary", ""),
        "key_topics": summary_data.get("key_topics", []),
        "action_items": action_items,
        "decisions": decisions,
        "risks": risks,
        "deadlines": deadlines
    }
    
    # Validate
    validation = validate_meeting_output(payload)
    if not validation["report"]["valid"]:
        logger.warning(f"Validation errors: {validation['report']['errors']}")
        
    # Save to DB
    # We pass file_id as meeting_id
    try:
        db_meeting = crud.save_meeting_result(db, file_id, validation["payload"], matched_file)
    except Exception as e:
        logger.error(f"DB save error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save results to database")
        
    # Audit log
    audit_data = {
        "event": "audit",
        "action": "process_meeting",
        "meeting_id": file_id,
        "filename": matched_file,
        "user": "Anonymous User",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"AUDIT LOG: {json.dumps(audit_data)}")
        
    return {"meeting_id": file_id, "status": "processed"}

@app.get("/api/meetings/{meeting_id}", tags=["API"])
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = crud.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    return {
        "id": meeting.id,
        "filename": meeting.filename,
        "upload_timestamp": meeting.upload_timestamp.isoformat() if meeting.upload_timestamp else None,
        "meeting_date": meeting.meeting_date,
        "summary": meeting.raw_summary,
        "key_topics": json.loads(meeting.key_topics),
        "action_items": [
            {
                "task": ai.task, "owner": ai.owner, "deadline": ai.deadline, "source_chunk": ai.source_chunk
            } for ai in meeting.action_items
        ],
        "decisions": [
            {
                "decision": d.decision, "context": d.context, "source_chunk": d.source_chunk
            } for d in meeting.decisions
        ],
        "risks": [
            {
                "risk": r.risk, "severity": r.severity, "source_chunk": r.source_chunk
            } for r in meeting.risks
        ],
        "deadlines": [
            {
                "deadline_text": d.deadline_text, "normalized_date": d.normalized_date, "related_task": d.related_task
            } for d in meeting.deadlines
        ]
    }

@app.get("/api/search", tags=["API"])
def search_meetings(q: str, db: Session = Depends(get_db)):
    if not q or len(q.strip()) == 0:
        return []
    results = crud.search_meetings(db, q.strip())
    
    # Return brief summaries
    return [
        {
            "id": m.id,
            "filename": m.filename,
            "upload_timestamp": m.upload_timestamp.isoformat() if m.upload_timestamp else None,
            "summary": m.raw_summary[:200] + "..." if len(m.raw_summary) > 200 else m.raw_summary,
        } for m in results
    ]

@app.get("/api/meetings/{meeting_id}/export", tags=["API"])
def export_meeting_report(meeting_id: str, format: str = "pdf", db: Session = Depends(get_db)):
    if format not in ["md", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'md' or 'pdf'.")
        
    logger.info(f"Exporting report for meeting {meeting_id} in {format} format")
    try:
        filepath = generate_report(db, meeting_id, format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")
        
    filename = os.path.basename(filepath)
    media_type = "application/pdf" if format == "pdf" else "text/markdown"
    
    return FileResponse(
        filepath, 
        media_type=media_type, 
        filename=filename
    )

# Mount frontend static files last as catch-all
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")