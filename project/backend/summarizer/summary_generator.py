import json
import os
import logging
from typing import List, Dict, Any
from llm_client import call_llm

logger = logging.getLogger("summary_generator")

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

def call_llm_with_json_validation(prompt: str, system_prompt: str) -> Dict[str, Any]:
    """
    Call the LLM and validate that the output is valid JSON.
    If parsing fails, retries once with stricter JSON instructions.
    """
    response_text = call_llm(prompt, system=system_prompt)
    
    # Try to parse JSON
    try:
        return json.loads(response_text)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Initial LLM response was not valid JSON: {str(e)}. Retrying once...")
        
        # Build strict retry prompt
        strict_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL WARNING: Your previous response was invalid JSON. "
            f"You MUST return only a valid, raw JSON object matching the requested schema. "
            f"Do NOT wrap in markdown code blocks or write any explanation."
        )
        
        retry_response_text = call_llm(strict_prompt, system=system_prompt)
        try:
            return json.loads(retry_response_text)
        except (json.JSONDecodeError, TypeError, ValueError) as retry_error:
            logger.error(f"LLM response failed JSON validation on retry: {str(retry_error)}")
            raise ValueError(
                f"LLM output could not be parsed as valid JSON. "
                f"Raw response: {retry_response_text}"
            ) from retry_error

def generate_summary(chunks: List[str]) -> Dict[str, Any]:
    """
    Generates a consolidated meeting summary from transcript chunks using a map-reduce approach.

    Args:
        chunks (list): List of string segments from the parsed transcript.

    Returns:
        dict: A dictionary containing:
            - summary (str): Consolidated overall summary.
            - key_topics (list): Main topics/summary points discussed.
            - meeting_length_chunks (int): Number of input chunks.
    """
    # 1. Handle empty transcript input
    if not chunks or all(not str(chunk).strip() for chunk in chunks):
        raise ValueError("Empty transcript provided")

    # Clean the input chunks list
    cleaned_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    num_chunks = len(cleaned_chunks)

    # Load templates
    system_prompt = read_prompt_template("system_prompt.txt")
    summary_template = read_prompt_template("summary_prompt.txt")

    # 2. Summarize each chunk (Map phase)
    chunk_summaries = []
    for index, chunk in enumerate(cleaned_chunks):
        logger.info(f"Summarizing chunk {index + 1}/{num_chunks}")
        prompt = summary_template.format(transcript_chunk=chunk)
        
        chunk_data = call_llm_with_json_validation(prompt, system_prompt)
        chunk_summaries.append(chunk_data)

    # 3. Consolidate summaries (Reduce phase)
    if num_chunks == 1:
        # For a single chunk, map results directly to final output format
        final_summary_data = chunk_summaries[0]
    else:
        # Combine intermediate summaries
        combined_summaries_text = ""
        for i, s in enumerate(chunk_summaries):
            title = s.get("title", f"Segment {i+1}")
            overall = s.get("overall_summary", "")
            points = "\n".join([f"- {pt}" for pt in s.get("summary_points", [])])
            
            combined_summaries_text += (
                f"Topic: {title}\n"
                f"Summary: {overall}\n"
                f"Discussion Points:\n{points}\n\n"
            )

        logger.info("Consolidating intermediate segment summaries...")
        prompt = summary_template.format(transcript_chunk=combined_summaries_text)
        final_summary_data = call_llm_with_json_validation(prompt, system_prompt)

    # Extract final fields
    return {
        "summary": final_summary_data.get("overall_summary", "").strip(),
        "key_topics": final_summary_data.get("summary_points", []),
        "meeting_length_chunks": num_chunks
    }
