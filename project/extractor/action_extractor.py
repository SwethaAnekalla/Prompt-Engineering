import json
import os
import logging
from typing import List, Dict, Any
from backend.llm_client import call_llm

logger = logging.getLogger("action_extractor")

# Resolve directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

def read_prompt_template(filename: str) -> str:
    """Read a prompt template file from the prompts directory."""
    path = os.path.join(PROMPTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read prompt template {filename}: {str(e)}")
        raise RuntimeError(f"Failed to read prompt template: {filename}") from e

def call_extractor_llm(prompt: str, system_prompt: str, key_name: str) -> List[Dict[str, Any]]:
    """
    Calls the LLM, validates that the output is valid JSON containing the expected list under key_name.
    If parsing or format verification fails, retries once with stricter instructions.
    """
    response_text = call_llm(prompt, system=system_prompt)
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and key_name in data and isinstance(data[key_name], list):
            return data[key_name]
        raise ValueError(f"Expected dictionary with key '{key_name}' containing a list")
    except Exception as e:
        logger.warning(f"Initial extraction for '{key_name}' failed: {str(e)}. Retrying once...")

        strict_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL WARNING: Your previous response was invalid. "
            f"You MUST return only a valid, raw JSON object matching the requested schema. "
            f"It must contain a key '{key_name}' whose value is a JSON list. "
            f"Do NOT wrap in markdown code blocks or write any explanation."
        )

        retry_response_text = call_llm(strict_prompt, system=system_prompt)
        try:
            data = json.loads(retry_response_text)
            if isinstance(data, dict) and key_name in data and isinstance(data[key_name], list):
                return data[key_name]
            raise ValueError(f"Expected dictionary with key '{key_name}' containing a list on retry")
        except Exception as retry_error:
            logger.error(f"Extraction for '{key_name}' failed on retry: {str(retry_error)}")
            raise RuntimeError(f"Extraction failed: {str(retry_error)}") from retry_error

def extract_action_items(chunks: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts action items from transcript chunks.
    
    Args:
        chunks (list): List of text segment chunks.

    Returns:
        list: List of dicts matching:
            { "task": str, "owner": str|null, "deadline": str|null, "source_chunk": int }
    """
    if not chunks:
        return []

    system_prompt = read_prompt_template("system_prompt.txt")
    template = read_prompt_template("action_item_prompt.txt")

    all_items = []
    for chunk_idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        prompt = template.format(transcript_chunk=chunk)
        raw_items = call_extractor_llm(prompt, system_prompt, "action_items")

        for item in raw_items:
            task = item.get("task", "")
            if not task:
                continue

            owner = item.get("owner")
            if owner in ["Unassigned", "unassigned", "", None]:
                owner = None

            deadline = item.get("deadline")
            if deadline in ["None", "none", "", None]:
                deadline = None

            all_items.append({
                "task": str(task).strip(),
                "owner": owner,
                "deadline": deadline,
                "source_chunk": chunk_idx
            })

    return all_items

def extract_decisions(chunks: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts key decisions made from transcript chunks.

    Args:
        chunks (list): List of text segment chunks.

    Returns:
        list: List of dicts matching:
            { "decision": str, "context": str, "source_chunk": int }
    """
    if not chunks:
        return []

    system_prompt = read_prompt_template("system_prompt.txt")
    template = read_prompt_template("decision_prompt.txt")

    all_items = []
    for chunk_idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        prompt = template.format(transcript_chunk=chunk)
        raw_items = call_extractor_llm(prompt, system_prompt, "decisions")

        for item in raw_items:
            decision = item.get("decision", "")
            if not decision:
                continue

            context = item.get("context", "")

            all_items.append({
                "decision": str(decision).strip(),
                "context": str(context).strip(),
                "source_chunk": chunk_idx
            })

    return all_items

def extract_risks(chunks: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts risks/blockers from transcript chunks.

    Args:
        chunks (list): List of text segment chunks.

    Returns:
        list: List of dicts matching:
            { "risk": str, "severity": "low"|"medium"|"high", "source_chunk": int }
    """
    if not chunks:
        return []

    system_prompt = read_prompt_template("system_prompt.txt")
    template = read_prompt_template("risk_prompt.txt")

    all_items = []
    for chunk_idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        prompt = template.format(transcript_chunk=chunk)
        raw_items = call_extractor_llm(prompt, system_prompt, "risks")

        for item in raw_items:
            risk = item.get("risk", "")
            if not risk:
                continue

            severity = str(item.get("severity", "medium")).lower().strip()
            if severity not in ["low", "medium", "high"]:
                severity = "medium"

            all_items.append({
                "risk": str(risk).strip(),
                "severity": severity,
                "source_chunk": chunk_idx
            })

    return all_items

def extract_deadlines(chunks: List[str], meeting_date: str = None) -> List[Dict[str, Any]]:
    """
    Extracts deadlines and timeline milestones from transcript chunks.

    Args:
        chunks (list): List of text segment chunks.
        meeting_date (str, optional): The meeting's recorded date in YYYY-MM-DD.

    Returns:
        list: List of dicts matching:
            { "deadline_text": str, "normalized_date": str|null, "related_task": str|null }
    """
    if not chunks:
        return []

    system_prompt = read_prompt_template("system_prompt.txt")
    template = read_prompt_template("deadline_prompt.txt")

    meeting_date_context = meeting_date if meeting_date else "Unknown"

    all_items = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        prompt = template.format(
            meeting_date_context=meeting_date_context,
            transcript_chunk=chunk
        )
        raw_items = call_extractor_llm(prompt, system_prompt, "deadlines")

        for item in raw_items:
            deadline_text = item.get("deadline_text", "")
            if not deadline_text:
                continue

            normalized_date = item.get("normalized_date")
            if normalized_date in ["", "null", "None", None]:
                normalized_date = None

            related_task = item.get("related_task")
            if related_task in ["", "null", "None", None]:
                related_task = None

            all_items.append({
                "deadline_text": str(deadline_text).strip(),
                "normalized_date": normalized_date,
                "related_task": related_task
            })

    return all_items
