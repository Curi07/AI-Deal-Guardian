import pytest
from unittest.mock import patch, MagicMock
from app.llm.provider import GroqProvider
from pydantic import BaseModel
import json
from app.schemas.deal import Deal
from app.schemas.analysis import ScopeDiff, IntentAnalysis, DealContextSummary, Strategy, ResponseDraft

class DummyResponseModel(BaseModel):
    message: str
    confidence: float

def test_groq_provider_success():
    provider = GroqProvider(api_key="test_key", model="openai/gpt-oss-20b")
    
    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = json.dumps({"message": "Hello from mock Groq", "confidence": 0.99})
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    result = provider.generate_structured(
        system_prompt="You are a helpful assistant",
        user_prompt="Say hello",
        response_model=DummyResponseModel
    )

    assert isinstance(result, DummyResponseModel)
    assert result.message == "Hello from mock Groq"
    assert result.confidence == 0.99
    
    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "openai/gpt-oss-20b"
    assert "tools" in call_args.kwargs
    assert call_args.kwargs["tools"][0]["type"] == "function"
    assert call_args.kwargs["tool_choice"] == {"type": "function", "function": {"name": "generate_response"}}

def test_groq_provider_schema_sanitization():
    provider = GroqProvider(api_key="test_key")

    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = json.dumps({"test_val": "ok", "opt_val": "present"})
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    class NestedModel(BaseModel):
        nested_val: str = "default_nested"
        
    class ComplexModel(BaseModel):
        test_val: str = "default_string"
        opt_val: str | None = None
        nested: NestedModel = NestedModel()

    provider.generate_structured("system", "user", ComplexModel)

    call_args = provider.client.chat.completions.create.call_args
    schema_sent = call_args.kwargs["tools"][0]["function"]["parameters"]

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

def test_groq_provider_dynamic_models():
    provider = GroqProvider(api_key="test_key")

    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = json.dumps({
        "intent": {"primary": "negotiation", "confidence": 0.9},
        "deal_context": {"summary": "test", "relevant_decisions": []}
    })
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    class PartialMessageAnalysis(BaseModel):
        intent: IntentAnalysis
        deal_context: DealContextSummary
        
    result = provider.generate_structured("system", "user", PartialMessageAnalysis)
    assert isinstance(result, PartialMessageAnalysis)

    # Now test Stage2Result
    mock_tool_call.function.arguments = json.dumps({
        "strategy": {"objective": "defend", "recommended_action": "do it", "reasoning": [], "key_points": []},
        "response": {"draft": "hello", "tone": "pro", "requires_review": True}
    })
    
    class Stage2Result(BaseModel):
        strategy: Strategy
        response: ResponseDraft

    result = provider.generate_structured("system", "user", Stage2Result)
    assert isinstance(result, Stage2Result)
