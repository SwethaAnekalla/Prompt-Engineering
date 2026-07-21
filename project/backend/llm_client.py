import os
import time
import random
import logging
import httpx

logger = logging.getLogger("llm_client")

def call_llm(prompt: str, system: str = None) -> str:
    """
    Call the Gemini API with the provided prompt and optional system instructions.
    Retries with exponential backoff + jitter on transient failures
    (429 or 5xx status codes, or connection/timeout errors).

    Args:
        prompt (str): The user prompt.
        system (str, optional): The system prompt defining assistant behavior.

    Returns:
        str: Raw JSON string returned by the LLM.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key   # <-- auth keys go in the header, not the URL
    }

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    max_attempts = 5          # was 2 -> more room to ride out rate limits
    base_delay = 2.0          # seconds, doubles each retry
    max_delay = 30.0          # cap on backoff wait
    timeout_seconds = 120.0   # was 60 -> Gemini can be slow under load

    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Calling LLM API ({model}) - Attempt {attempt}/{max_attempts}")
            response = httpx.post(api_url, json=payload, headers=headers, timeout=timeout_seconds)

            if response.status_code in [429, 500, 502, 503, 504]:
                if attempt < max_attempts:
                    # Respect Retry-After header if Gemini sends one, else exponential backoff + jitter
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait = float(retry_after)
                    else:
                        wait = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        wait += random.uniform(0, 1)  # jitter avoids retry storms

                    logger.warning(
                        f"Transient HTTP error {response.status_code} received. "
                        f"Body: {response.text[:500]} "
                        f"Retrying in {wait:.1f} seconds..."
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.error(f"Final failure body: {response.text[:1000]}")
                    response.raise_for_status()

            response.raise_for_status()

            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Network or HTTP error on attempt {attempt}: {str(e)}")
            last_exception = e
            if attempt < max_attempts:
                wait = min(base_delay * (2 ** (attempt - 1)), max_delay)
                wait += random.uniform(0, 1)
                time.sleep(wait)
                continue
            else:
                raise RuntimeError(f"API failure: {str(e)}") from e

    raise RuntimeError(f"API failure after {max_attempts} attempts: {str(last_exception)}") from last_exception