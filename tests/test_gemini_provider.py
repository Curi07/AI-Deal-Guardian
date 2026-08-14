import pytest
from unittest.mock import patch, MagicMock
from app.llm.provider import GeminiProvider
from pydantic import BaseModel
import json
from app.schemas.deal import Deal
from app.schemas.analysis import ScopeDiff

class DummyResponseModel(BaseModel):
    message: str
    confidence: float

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_success(mock_client_class):
    # Setup mock
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({"message": "Hello from mock Gemini", "confidence": 0.99})
    mock_client.models.generate_content.return_value = mock_response

    # Initialize provider
    provider = GeminiProvider(api_key="test_key", model="gemini-1.5-flash")
    
    # Execute
    result = provider.generate_structured(
        system_prompt="You are a helpful assistant",
        user_prompt="Say hello",
        response_model=DummyResponseModel
    )

    # Assertions
    assert isinstance(result, DummyResponseModel)
    assert result.message == "Hello from mock Gemini"
    assert result.confidence == 0.99
    
    mock_client_class.assert_called_once_with(api_key="test_key")
    mock_client.models.generate_content.assert_called_once()
    
    call_args = mock_client.models.generate_content.call_args
    assert call_args.kwargs["model"] == "gemini-1.5-flash"
    assert call_args.kwargs["contents"] == "Say hello"
    assert call_args.kwargs["config"].response_mime_type == "application/json"
    assert call_args.kwargs["config"].system_instruction == "You are a helpful assistant"

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_json_error(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = "invalid json"
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key")
    
    with pytest.raises(ValueError, match="Failed to decode JSON from Gemini: invalid json"):
        provider.generate_structured("system", "user", DummyResponseModel)

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_generate_deal(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    # Mocking a basic deal JSON response
    deal_json = {
        "client": {"name": "Test Client"},
        "project": {"title": "Test Project", "type": "", "description": ""},
        "commercial": {"budget": 1000},
        "timeline": {"deadline": "1 week"},
        "scope": {"deliverables": ["A", "B"], "exclusions": [], "assumptions": []},
        "requirements": [
            {"id": "r1", "description": "Req1", "source": "client", "certainty": "explicit"}
        ],
        "dependencies": [
            {"description": "Dep1", "status": "pending", "owner": "client"}
        ],
        "unknowns": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready", "risk_score": 0, "confidence": 0.9, "blocking_unknowns": 0},
        "risks": [],
        "questions": []
    }
    mock_response.text = json.dumps(deal_json)
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key", model="gemini-1.5-flash")
    
    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=Deal
    )

    assert isinstance(result, Deal)
    assert result.client.name == "Test Client"
    assert result.commercial.budget == 1000

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_generate_scopediff(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    # Mocking a ScopeDiff JSON response
    scopediff_json = {
        "added": ["Feature A"],
        "removed": [],
        "changed": [],
        "conflicting": [],
        "unchanged": [],
        "classification": "in_scope",
        "evidence": ["test evidence"],
        "commercial_impact": {"level": "none", "reason": "test", "pricing_action": "test"},
        "recommended_action": "proceed"
    }
    mock_response.text = json.dumps(scopediff_json)
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key", model="gemini-1.5-flash")
    
    result = provider.generate_structured(
        system_prompt="system",
        user_prompt="user",
        response_model=ScopeDiff
    )

    assert isinstance(result, ScopeDiff)
    assert result.classification == "in_scope"
    assert result.added == ["Feature A"]
