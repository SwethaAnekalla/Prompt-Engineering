import os
import json
from fpdf import FPDF
from database import crud
from sqlalchemy.orm import Session
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Meeting Minutes & Action Items', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def table_header(self, cols):
        self.set_font('helvetica', 'B', 11)
        # Assuming equal widths for simplicity based on number of cols
        w = 190 / len(cols)
        for col in cols:
            self.cell(w, 8, col, 1, 0, 'C', 1)
        self.ln()

    def table_row(self, row, cols_count):
        self.set_font('helvetica', '', 10)
        w = 190 / cols_count
        # This is a very simple table that doesn't handle multi-line text well in FPDF natively.
        # But for this assignment, a simple cell works.
        # To handle long text better, we would need multi_cell or calculate max height.
        # We will truncate for simplicity, or use multi_cell with some math.
        # Using multi_cell inside a row is complex in pure FPDF, so we'll truncate strings for PDF.
        max_chars = int(w / 2) # rough estimate
        for item in row:
            text = str(item).replace('\n', ' ')
            if len(text) > max_chars:
                text = text[:max_chars-3] + '...'
            self.cell(w, 8, text, 1, 0, 'L')
        self.ln()

def generate_markdown_report(meeting) -> str:
    lines = []
    lines.append(f"# Meeting Minutes Report")
    lines.append(f"**Filename:** {meeting.filename}")
    date_str = meeting.meeting_date if meeting.meeting_date else (meeting.upload_timestamp.strftime("%Y-%m-%d %H:%M:%S") if meeting.upload_timestamp else 'Unknown')
    lines.append(f"**Date:** {date_str}")
    lines.append("\n## Executive Summary")
    lines.append(meeting.raw_summary if meeting.raw_summary else "No summary available.")
    
    key_topics = json.loads(meeting.key_topics) if meeting.key_topics else []
    if key_topics:
        lines.append("\n**Key Topics:** " + ", ".join(key_topics))
    
    lines.append("\n## Action Items")
    if meeting.action_items:
        lines.append("| Task | Owner | Deadline |")
        lines.append("|---|---|---|")
        for ai in meeting.action_items:
            owner = ai.owner or "Unassigned"
            deadline = ai.deadline or "None"
            # escape pipes if any
            task = ai.task.replace('|', '\\|').replace('\n', ' ')
            lines.append(f"| {task} | {owner} | {deadline} |")
    else:
        lines.append("No action items identified.")
        
    lines.append("\n## Decisions")
    if meeting.decisions:
        for d in meeting.decisions:
            lines.append(f"- **{d.decision}**: {d.context}")
    else:
        lines.append("No decisions identified.")
        
    lines.append("\n## Risks")
    if meeting.risks:
        for r in meeting.risks:
            lines.append(f"- [{r.severity.upper()}] {r.risk}")
    else:
        lines.append("No risks identified.")
        
    lines.append("\n## Deadlines")
    if meeting.deadlines:
        for d in meeting.deadlines:
            date_n = d.normalized_date or "Unspecified"
            rel = d.related_task or "None"
            lines.append(f"- **{d.deadline_text}** (Parsed: {date_n}) - Task: {rel}")
    else:
        lines.append("No deadlines identified.")
        
    filepath = os.path.join(EXPORT_DIR, f"{meeting.id}_report.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath

def generate_pdf_report(meeting) -> str:
    pdf = PDFReport()
    pdf.add_page()
    
    # Metadata
    date_str = meeting.meeting_date if meeting.meeting_date else (meeting.upload_timestamp.strftime("%Y-%m-%d %H:%M:%S") if meeting.upload_timestamp else 'Unknown')
    pdf.set_font('helvetica', '', 11)
    pdf.cell(0, 6, f"Filename: {meeting.filename}", 0, 1)
    pdf.cell(0, 6, f"Date: {date_str}", 0, 1)
    pdf.ln(5)
    
    # Summary
    pdf.chapter_title("Executive Summary")
    pdf.chapter_body(meeting.raw_summary if meeting.raw_summary else "No summary available.")
    
    key_topics = json.loads(meeting.key_topics) if meeting.key_topics else []
    if key_topics:
        pdf.set_font('helvetica', 'B', 11)
        pdf.cell(0, 6, "Key Topics: " + ", ".join(key_topics), 0, 1)
        pdf.ln(4)
        
    # Action Items
    pdf.chapter_title("Action Items")
    if meeting.action_items:
        cols = ["Task", "Owner", "Deadline"]
        pdf.table_header(cols)
        for ai in meeting.action_items:
            owner = ai.owner or "Unassigned"
            deadline = ai.deadline or "None"
            pdf.table_row([ai.task, owner, deadline], len(cols))
        pdf.ln(4)
    else:
        pdf.chapter_body("No action items identified.")
        
    # Decisions
    pdf.chapter_title("Decisions")
    if meeting.decisions:
        for d in meeting.decisions:
            pdf.chapter_body(f"- {d.decision} (Context: {d.context})")
    else:
        pdf.chapter_body("No decisions identified.")
        
    # Risks
    pdf.chapter_title("Risks")
    if meeting.risks:
        for r in meeting.risks:
            pdf.chapter_body(f"- [{r.severity.upper()}] {r.risk}")
    else:
        pdf.chapter_body("No risks identified.")
        
    # Deadlines
    pdf.chapter_title("Deadlines")
    if meeting.deadlines:
        for d in meeting.deadlines:
            date_n = d.normalized_date or "Unspecified"
            rel = d.related_task or "None"
            pdf.chapter_body(f"- {d.deadline_text} (Parsed: {date_n}) - Task: {rel}")
    else:
        pdf.chapter_body("No deadlines identified.")
        
    filepath = os.path.join(EXPORT_DIR, f"{meeting.id}_report.pdf")
    pdf.output(filepath)
    return filepath

def generate_report(db: Session, meeting_id: str, format: str) -> str:
    """
    Generates a report for the given meeting ID.
    Format must be 'md' or 'pdf'.
    Returns the absolute path to the generated file.
    """
    meeting = crud.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise ValueError(f"Meeting with ID {meeting_id} not found.")
        
    if format == 'md':
        return generate_markdown_report(meeting)
    elif format == 'pdf':
        return generate_pdf_report(meeting)
    else:
        raise ValueError(f"Unsupported format '{format}'. Use 'md' or 'pdf'.")
