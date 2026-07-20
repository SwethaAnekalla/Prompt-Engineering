import os
import time
import logging
import httpx

logger = logging.getLogger("llm_client")

def call_llm(prompt: str, system: str = None) -> str:
    """
    Call the LLM API (OpenAI compatible) with the provided prompt and optional system instructions.
    Implements a single retry on transient failures (429 or 5xx status codes, or connection errors).

    Args:
        prompt (str): The user prompt.
        system (str, optional): The system prompt defining assistant behavior.

    Returns:
        str: Raw JSON string returned by the LLM.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    api_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Calling LLM API ({model}) - Attempt {attempt}/{max_attempts}")
            response = httpx.post(api_url, json=payload, headers=headers, timeout=60.0)
            
            # Check for transient server errors or rate limits
            if response.status_code in [429, 500, 502, 503, 504]:
                if attempt < max_attempts:
                    logger.warning(f"Transient HTTP error {response.status_code} received. Retrying in 1 second...")
                    time.sleep(1)
                    continue
                else:
                    response.raise_for_status()
            
            # Raise for any other non-2xx status codes
            response.raise_for_status()

            result = response.json()
            # Return the text content containing raw JSON
            return result["choices"][0]["message"]["content"].strip()

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Network or HTTP error on attempt {attempt}: {str(e)}")
            if attempt < max_attempts:
                time.sleep(1)
                continue
            else:
                raise RuntimeError(f"API failure: {str(e)}") from e
