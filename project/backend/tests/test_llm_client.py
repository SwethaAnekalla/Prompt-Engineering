import os
import pytest
from unittest.mock import patch, MagicMock
import httpx
from llm_client import call_llm

@pytest.fixture
def mock_env_api_key():
    """Fixture to mock the environment API key."""
    old_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "mock-api-key"
    yield
    if old_key is not None:
        os.environ["OPENAI_API_KEY"] = old_key
    else:
        del os.environ["OPENAI_API_KEY"]

def test_call_llm_missing_api_key():
    """Verify that a ValueError is raised when OPENAI_API_KEY is not set."""
    # Ensure OPENAI_API_KEY is unset
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
            call_llm("Hello")

@patch("httpx.post")
def test_call_llm_success(mock_post, mock_env_api_key):
    """Verify successful LLM calls return the expected content."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"summary": "Test summary"}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    result = call_llm("summarize this text", system="system prompt")
    
    assert result == '{"summary": "Test summary"}'
    # Assert headers and payload were passed correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer mock-api-key"
    assert kwargs["json"]["messages"][0] == {"role": "system", "content": "system prompt"}
    assert kwargs["json"]["messages"][1] == {"role": "user", "content": "summarize this text"}

@patch("httpx.post")
@patch("time.sleep", return_value=None) # Speed up test
def test_call_llm_transient_failure_retry_success(mock_sleep, mock_post, mock_env_api_key):
    """Verify that call_llm retries on a transient error and succeeds if the retry works."""
    # Create responses: first is a 500 error, second is a 200 success
    response_500 = MagicMock()
    response_500.status_code = 500
    response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=response_500
    )
    
    response_200 = MagicMock()
    response_200.status_code = 200
    response_200.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"items": []}'
                }
            }
        ]
    }
    
    mock_post.side_effect = [response_500, response_200]

    result = call_llm("test prompt")
    
    assert result == '{"items": []}'
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1)

@patch("httpx.post")
@patch("time.sleep", return_value=None) # Speed up test
def test_call_llm_persistent_failure(mock_sleep, mock_post, mock_env_api_key):
    """Verify that call_llm raises a RuntimeError after retrying and failing twice."""
    response_500 = MagicMock()
    response_500.status_code = 500
    response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=response_500
    )
    
    mock_post.return_value = response_500

    with pytest.raises(RuntimeError, match="API failure"):
        call_llm("test prompt")
        
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1)
