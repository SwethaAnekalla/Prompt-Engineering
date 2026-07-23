from dotenv import load_dotenv
load_dotenv()

import os
import time
import random
import logging
import json
from google import genai

logger = logging.getLogger("llm_client")

def call_llm(prompt: str, system: str = None) -> str:
    """
    Call the Gemini API using the new google-genai SDK.
    Retries with exponential backoff + jitter on transient failures.
    Falls back to a secondary model after repeated failures on the primary.

    If DEMO_MODE=true in .env, returns mock JSON data instead of calling the API.

    Args:
        prompt (str): The user prompt.
        system (str, optional): The system prompt defining assistant behavior.

    Returns:
        str: Raw JSON string returned by the LLM or mock data.
    """
    # Check for demo mode
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

    if demo_mode:
        logger.info("DEMO MODE: Returning mock data instead of calling API")
        if "summary" in prompt.lower() or "summarize" in prompt.lower():
            return json.dumps({
                "summary": "This is a demo meeting summary. The team discussed project milestones, budget allocation, and upcoming deliverables. Key stakeholders provided updates on their respective areas.",
                "key_topics": ["Project Timeline", "Budget Review", "Team Updates", "Risk Assessment"],
                "chunk_summary": "Demo chunk discussing various project aspects and team collaboration."
            })
        elif "action" in prompt.lower():
            return json.dumps({
                "action_items": [
                    {"task": "Complete project documentation", "owner": "John Doe", "deadline": "Next Friday", "source_chunk": 1},
                    {"task": "Review budget proposal", "owner": "Jane Smith", "deadline": "End of week", "source_chunk": 2},
                    {"task": "Schedule follow-up meeting", "owner": "Team Lead", "deadline": "Tomorrow", "source_chunk": 3}
                ]
            })
        elif "decision" in prompt.lower():
            return json.dumps({
                "decisions": [
                    {"decision": "Approved budget increase for Q2", "context": "Based on projected growth", "source_chunk": 1},
                    {"decision": "Extended project deadline by 2 weeks", "context": "To ensure quality deliverables", "source_chunk": 2}
                ]
            })
        elif "risk" in prompt.lower():
            return json.dumps({
                "risks": [
                    {"risk": "Potential resource shortage", "severity": "Medium", "source_chunk": 1},
                    {"risk": "Timeline constraints for Phase 2", "severity": "High", "source_chunk": 2}
                ]
            })
        elif "deadline" in prompt.lower():
            return json.dumps({
                "deadlines": [
                    {"deadline_text": "Project completion by March 31", "normalized_date": "2026-03-31", "related_task": "Final deliverables"},
                    {"deadline_text": "Review meeting next Friday", "normalized_date": "2026-07-25", "related_task": "Budget review"}
                ]
            })
        else:
            return json.dumps({"result": "Demo data", "status": "success"})

    # Get API key and models from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

    max_attempts = 3
    base_delay = 1.0
    max_delay = 8.0
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        # Use the primary model for the first 3 attempts, then switch to fallback
        current_model = model_name if attempt <= 3 else fallback_model
        try:
            logger.info(f"Calling Gemini API ({current_model}) using google-genai SDK - Attempt {attempt}/{max_attempts}")

            client = genai.Client(api_key=api_key)

            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            config = {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }

            response = client.models.generate_content(
                model=current_model,
                contents=full_prompt,
                config=config
            )

            logger.info("API call successful")
            return response.text.strip()

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error on attempt {attempt} ({current_model}): {error_msg}")
            last_exception = e

            if attempt < max_attempts:
                wait = min(base_delay * (2 ** (attempt - 1)), max_delay)
                wait += random.uniform(0, 1)
                logger.warning(f"Retrying in {wait:.1f} seconds...")
                time.sleep(wait)
                continue

    raise RuntimeError(f"API failure after {max_attempts} attempts: {str(last_exception)}") from last_exception