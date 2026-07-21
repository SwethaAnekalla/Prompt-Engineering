import pytest
from unittest.mock import patch
from summarizer.summary_generator import generate_summary

@pytest.fixture
def mock_env_api_key():
    """Fixture to ensure OPENAI_API_KEY is present for tests."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
        yield

def test_generate_summary_empty_input():
    """Verify that empty inputs raise a ValueError without calling the LLM."""
    with pytest.raises(ValueError, match="Empty transcript provided"):
        generate_summary([])

    with pytest.raises(ValueError, match="Empty transcript provided"):
        generate_summary(["   ", "\n  \n"])

@patch("summarizer.summary_generator.call_llm")
def test_generate_summary_single_chunk(mock_call_llm, mock_env_api_key):
    """Verify that a single-chunk transcript maps directly to the output without a reduce phase."""
    mock_response = (
        '{"title": "Intro and Setup", '
        '"overall_summary": "The team established the project repository and configured folders.", '
        '"summary_points": ["Repository created", "Scaffolding finished"], '
        '"key_takeaways": ["Repo ready for upload module"]}'
    )
    mock_call_llm.return_value = mock_response

    result = generate_summary(["Alice: Hi. Bob: Hello. Let's create the repository."])
    
    assert result["meeting_length_chunks"] == 1
    assert result["summary"] == "The team established the project repository and configured folders."
    assert result["key_topics"] == ["Repository created", "Scaffolding finished"]
    mock_call_llm.assert_called_once()

@patch("summarizer.summary_generator.call_llm")
def test_generate_summary_multi_chunks(mock_call_llm, mock_env_api_key):
    """Verify that a multi-chunk transcript undergoes map and reduce phases."""
    # We have 2 chunks, so 3 calls to call_llm total (2 map phase calls, 1 reduce phase call)
    map1_response = (
        '{"title": "Frontend discussion", '
        '"overall_summary": "Discussed React vs Vue.", '
        '"summary_points": ["React chosen", "Vite configured"], '
        '"key_takeaways": ["React selected"]}'
    )
    map2_response = (
        '{"title": "Backend discussion", '
        '"overall_summary": "Discussed FastAPI routing.", '
        '"summary_points": ["FastAPI selected", "Upload endpoint defined"], '
        '"key_takeaways": ["FastAPI selected"]}'
    )
    reduce_response = (
        '{"title": "Combined Technical Sync", '
        '"overall_summary": "The team chose React and FastAPI for stack setup.", '
        '"summary_points": ["React chosen", "FastAPI chosen"], '
        '"key_takeaways": ["Stack finalized"]}'
    )

    mock_call_llm.side_effect = [map1_response, map2_response, reduce_response]

    chunks = ["Transcript chunk 1", "Transcript chunk 2"]
    result = generate_summary(chunks)

    assert result["meeting_length_chunks"] == 2
    assert result["summary"] == "The team chose React and FastAPI for stack setup."
    assert result["key_topics"] == ["React chosen", "FastAPI chosen"]
    assert mock_call_llm.call_count == 3

@patch("summarizer.summary_generator.call_llm")
@patch("time.sleep", return_value=None)
def test_generate_summary_malformed_json_retry_success(mock_sleep, mock_call_llm, mock_env_api_key):
    """Verify that a malformed JSON output triggers a retry and succeeds if the retry output is valid."""
    malformed_response = "Here is the summary in JSON format: {title: 'Failed'}"
    valid_response = (
        '{"title": "Sync", '
        '"overall_summary": "Recovered from malformed JSON.", '
        '"summary_points": ["Recovery success"], '
        '"key_takeaways": []}'
    )
    
    mock_call_llm.side_effect = [malformed_response, valid_response]

    result = generate_summary(["Transcript content"])
    
    assert result["summary"] == "Recovered from malformed JSON."
    assert result["key_topics"] == ["Recovery success"]
    assert mock_call_llm.call_count == 2  # 1 initial + 1 retry

@patch("summarizer.summary_generator.call_llm")
@patch("time.sleep", return_value=None)
def test_generate_summary_malformed_json_retry_failure(mock_sleep, mock_call_llm, mock_env_api_key):
    """Verify that if the LLM output is persistently malformed JSON, a ValueError is raised."""
    malformed_response_1 = "No JSON here."
    malformed_response_2 = "Still no JSON."
    
    mock_call_llm.side_effect = [malformed_response_1, malformed_response_2]

    with pytest.raises(ValueError, match="LLM output could not be parsed as valid JSON"):
        generate_summary(["Transcript content"])
        
    assert mock_call_llm.call_count == 2
