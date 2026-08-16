import pytest
from unittest.mock import patch, MagicMock
from app.llm.provider import GeminiProvider
from pydantic import BaseModel
import json
from app.schemas.deal import Deal
from app.schemas.analysis import ScopeDiff, IntentAnalysis, DealContextSummary, Strategy, ResponseDraft

class DummyResponseModel(BaseModel):
    message: str
    confidence: float

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({"message": "Hello from mock Gemini", "confidence": 0.99})
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key", model="gemini-3.1-flash-lite")
    
    result = provider.generate_structured(
        system_prompt="You are a helpful assistant",
        user_prompt="Say hello",
        response_model=DummyResponseModel
    )

    assert isinstance(result, DummyResponseModel)
    assert result.message == "Hello from mock Gemini"
    assert result.confidence == 0.99
    
    call_args = mock_client.models.generate_content.call_args
    assert call_args.kwargs["model"] == "gemini-3.1-flash-lite"
    assert call_args.kwargs["config"].response_mime_type == "application/json"
    assert call_args.kwargs["config"].max_output_tokens == 4096

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_schema_sanitization(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({"test_val": "ok", "opt_val": "present"})
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key")

    class NestedModel(BaseModel):
        nested_val: str = "default_nested"
        
    class ComplexModel(BaseModel):
        test_val: str = "default_string"
        opt_val: str | None = None
        nested: NestedModel = NestedModel()

    provider.generate_structured("system", "user", ComplexModel)

    call_args = mock_client.models.generate_content.call_args
    schema_sent = call_args.kwargs["config"].response_schema

    def assert_no_forbidden_keys(schema_obj):
        if isinstance(schema_obj, dict):
            assert "default" not in schema_obj
            assert "title" not in schema_obj
            assert "$defs" not in schema_obj
            for k, v in schema_obj.items():
                assert_no_forbidden_keys(v)
        elif isinstance(schema_obj, list):
            for item in schema_obj:
                assert_no_forbidden_keys(item)

    assert_no_forbidden_keys(schema_sent)
    assert "nested" in schema_sent["properties"]

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_generate_deal(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    deal_json = {
        "client": {"name": "Test Client"},
        "project": {"title": "Test Project", "type": "", "description": ""},
        "commercial": {"budget": 1000},
        "timeline": {"deadline": "1 week"},
        "scope": {"deliverables": ["A", "B"], "exclusions": [], "assumptions": []},
        "requirements": [{"id": "r1", "description": "Req1", "source": "client", "certainty": "explicit"}],
        "dependencies": [{"description": "Dep1", "status": "pending", "owner": "client"}],
        "unknowns": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready", "risk_score": 0, "confidence": 0.9, "blocking_unknowns": 0},
        "risks": [],
        "questions": []
    }
    mock_response.text = json.dumps(deal_json)
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key", model="gemini-3.1-flash-lite")
    
    result = provider.generate_structured("system", "user", Deal)
    assert isinstance(result, Deal)

@patch('app.llm.provider.genai.Client')
def test_gemini_provider_dynamic_models(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "intent": {"primary": "negotiation", "confidence": 0.9},
        "deal_context": {"summary": "test", "relevant_decisions": []}
    })
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test_key", model="gemini-3.1-flash-lite")
    
    class PartialMessageAnalysis(BaseModel):
        intent: IntentAnalysis
        deal_context: DealContextSummary
        
    result = provider.generate_structured("system", "user", PartialMessageAnalysis)
    assert isinstance(result, PartialMessageAnalysis)

    # Now test Stage2Result
    mock_response.text = json.dumps({
        "strategy": {"objective": "defend", "recommended_action": "do it", "reasoning": [], "key_points": []},
        "response": {"draft": "hello", "tone": "pro", "requires_review": True}
    })
    
    class Stage2Result(BaseModel):
        strategy: Strategy
        response: ResponseDraft

    result = provider.generate_structured("system", "user", Stage2Result)
    assert isinstance(result, Stage2Result)
