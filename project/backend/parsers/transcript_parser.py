import io
import re
import os
from typing import List, Dict, Any

# Regular expressions for matching speaker patterns
# 1. Colon pattern (with optional timestamp): e.g. "John Doe (12:34): Hello" or "Speaker 1: Hi"
COLON_SPEAKER_PATTERN = re.compile(
    r"^\s*([A-Z][a-zA-Z0-9\s\.\-_]{0,49})(?:\s*[\(\[][0-9:]+[\)\]])?\s*:\s*(.*)$"
)
# 2. Bracket pattern: e.g. "[John Doe] Hello"
BRACKET_SPEAKER_PATTERN = re.compile(
    r"^\s*\[([A-Z][a-zA-Z0-9\s\.\-_]{0,49})\]\s*(.*)$"
)
# 3. Parentheses pattern: e.g. "(John Doe) Hello"
PARENTHESES_SPEAKER_PATTERN = re.compile(
    r"^\s*\(([A-Z][a-zA-Z0-9\s\.\-_]{0,49})\)\s*(.*)$"
)

# Common words to ignore to avoid identifying metadata fields as speakers
METADATA_BLOCKLIST = {
    "title", "date", "time", "location", "attendees", "note", "warning", 
    "http", "https", "agenda", "subject", "version", "status"
}

def parse_transcript(content: bytes, file_ext: str, max_chunk_chars: int = 4000) -> Dict[str, Any]:
    """
    Parses raw transcript content (from .txt or .docx), extracts speakers,
    cleans the text, and splits it into logical chunks.

    Args:
        content (bytes): Raw binary content of the file.
        file_ext (str): Extension of the file (e.g., '.txt', '.docx').
        max_chunk_chars (int): Character limit for downstream LLM chunking.

    Returns:
        dict: A dictionary containing:
            - raw_text (str): Complete, cleaned transcript text.
            - speakers (list): Sorted list of unique speaker names.
            - chunks (list): Ordered list of text chunks.
            - has_speaker_labels (bool): True if speaker patterns were detected.
    """
    if not content or len(content) == 0:
        raise ValueError("Empty transcript")

    normalized_ext = file_ext.lower().strip()
    if normalized_ext == ".txt":
        try:
            raw_text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise ValueError(f"Failed to decode text file: {str(e)}")
    elif normalized_ext == ".docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            raw_text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            raise ValueError(f"Failed to parse .docx file: {str(e)}")
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

    # Clean and check if empty
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Empty transcript")

    # Split into lines for analysis
    lines = raw_text.splitlines()
    
    parsed_lines = []
    detected_speakers = set()
    has_speaker_labels = False

    # Check each line for speaker patterns
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        matched_speaker = None
        matched_text = stripped_line

        # Try to match the speaker patterns
        for pattern in [COLON_SPEAKER_PATTERN, BRACKET_SPEAKER_PATTERN, PARENTHESES_SPEAKER_PATTERN]:
            match = pattern.match(stripped_line)
            if match:
                speaker_candidate = match.group(1).strip()
                # Check if it's just metadata or an empty candidate
                if speaker_candidate and speaker_candidate.lower() not in METADATA_BLOCKLIST:
                    matched_speaker = speaker_candidate
                    matched_text = match.group(2).strip()
                    break

        if matched_speaker:
            detected_speakers.add(matched_speaker)
            has_speaker_labels = True
            parsed_lines.append({
                "speaker": matched_speaker,
                "text": matched_text
            })
        else:
            # If we've already detected speakers in previous lines, attribute this line to the last speaker
            if parsed_lines and has_speaker_labels:
                last_speaker = parsed_lines[-1]["speaker"]
                parsed_lines.append({
                    "speaker": last_speaker,
                    "text": stripped_line
                })
            else:
                # Unattributed line
                parsed_lines.append({
                    "speaker": None,
                    "text": stripped_line
                })

    # Reconstruct cleaned text
    # If speaker labels are present, format as "Speaker: Text", otherwise just "Text"
    cleaned_lines = []
    for pl in parsed_lines:
        if pl["speaker"]:
            cleaned_lines.append(f"{pl['speaker']}: {pl['text']}")
        else:
            cleaned_lines.append(pl["text"])
    
    cleaned_raw_text = "\n".join(cleaned_lines)

    # Chunking logic
    chunks = []
    current_chunk = []
    current_len = 0

    for line_text in cleaned_lines:
        # Calculate length with a potential newline
        line_len = len(line_text) + (1 if current_chunk else 0)

        if current_len + line_len > max_chunk_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line_text]
                current_len = len(line_text)
            else:
                # If a single line is longer than the character limit, force it into a chunk
                chunks.append(line_text)
                current_chunk = []
                current_len = 0
        else:
            current_chunk.append(line_text)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return {
        "raw_text": cleaned_raw_text,
        "speakers": sorted(list(detected_speakers)),
        "chunks": chunks,
        "has_speaker_labels": has_speaker_labels
    }
