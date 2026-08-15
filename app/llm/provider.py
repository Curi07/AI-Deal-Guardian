import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel
import openai
from google import genai
from google.genai import types
from app.config import settings

T = TypeVar('T', bound=BaseModel)

class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        """Generates a structured response based on the Pydantic schema."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is missing. Please set it in the environment.")
        self.model = model or settings.llm_model
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        schema = response_model.model_json_schema()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        response_text = response.choices[0].message.content
        try:
            parsed_data = json.loads(response_text)
            return response_model(**parsed_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON from LLM: {response_text}") from e
        except Exception as e:
            raise ValueError(f"Failed to validate model {response_model.__name__} from LLM output: {response_text}") from e

def _sanitize_gemini_schema(schema: Dict[str, Any], defs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Recursively sanitize Pydantic JSON schema to be compatible with Gemini."""
    if defs is None:
        defs = schema.get("$defs", {})

    if not isinstance(schema, dict):
        if isinstance(schema, list):
            return [_sanitize_gemini_schema(item, defs) for item in schema]
        return schema

    sanitized = {}
    
    if "$ref" in schema:
        ref_key = schema["$ref"].split("/")[-1]
        if ref_key in defs:
            resolved = _sanitize_gemini_schema(defs[ref_key], defs)
            for k, v in schema.items():
                if k not in ["$ref", "default", "title"]:
                    resolved[k] = _sanitize_gemini_schema(v, defs)
            return resolved
            
    for k, v in schema.items():
        if k in ["default", "$defs", "title"]:
            continue
        sanitized[k] = _sanitize_gemini_schema(v, defs)
        
    return sanitized

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in the environment.")
        self.model = model or settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        print(f"[GEMINI] START response_model={response_model.__name__}")
        try:
            raw_schema = response_model.model_json_schema()
            schema = _sanitize_gemini_schema(raw_schema)
            
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0
            )
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config
            )
            
            response_text = response.text
            try:
                parsed_data = json.loads(response_text)
                result = response_model(**parsed_data)
                print(f"[GEMINI] SUCCESS response_model={response_model.__name__}")
                return result
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to decode JSON from Gemini: {response_text}") from e
            except Exception as e:
                raise ValueError(f"Failed to validate model {response_model.__name__} from Gemini output: {response_text}") from e
        except Exception as e:
            print(f"[GEMINI] ERROR response_model={response_model.__name__} error={e}")
            raise

class MockLLMProvider(LLMProvider):
    """A mock provider for testing purposes."""
    def __init__(self, mock_response: Any):
        self.mock_response = mock_response

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        if isinstance(self.mock_response, list):
            data = self.mock_response.pop(0) if self.mock_response else {}
        else:
            data = self.mock_response or {}
            
        model_name = response_model.__name__
        
        if model_name == "PartialMessageAnalysis":
            if "intent" not in data:
                data["intent"] = {
                    "primary": "new_requirement",
                    "confidence": 0.90
                }
            if "deal_context" not in data:
                data["deal_context"] = {}
                
        elif model_name == "Stage2Result":
            if "strategy" not in data:
                data["strategy"] = {
                    "objective": "negotiate_scope",
                    "recommended_action": "Negotiate scope additions.",
                    "reasoning": ["Client requested new requirement."],
                    "key_points": ["Cost impact", "Timeline impact"]
                }
            if "response" not in data:
                data["response"] = {
                    "draft": "We can add this, let's discuss the cost.",
                    "tone": "professional",
                    "requires_review": True
                }
                
        return response_model(**data)

def _sanitize_groq_schema(schema: Dict[str, Any], defs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Sanitize schema for Groq (similar constraints to Gemini)."""
    if defs is None:
        defs = schema.get("$defs", {})

    if not isinstance(schema, dict):
        if isinstance(schema, list):
            return [_sanitize_groq_schema(item, defs) for item in schema]
        return schema

    sanitized = {}
    
    if "$ref" in schema:
        ref_key = schema["$ref"].split("/")[-1]
        if ref_key in defs:
            resolved = _sanitize_groq_schema(defs[ref_key], defs)
            for k, v in schema.items():
                if k not in ["$ref", "default", "title"]:
                    resolved[k] = _sanitize_groq_schema(v, defs)
            return resolved
            
    for k, v in schema.items():
        if k in ["default", "$defs", "title"]:
            continue
        sanitized[k] = _sanitize_groq_schema(v, defs)
        
    return sanitized

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing. Please set it in the environment.")
        self.model = model or settings.groq_model
        # Use groq python sdk if installed, otherwise use openai wrapper
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            self.client = openai.OpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1")

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        raw_schema = response_model.model_json_schema()
        schema = _sanitize_groq_schema(raw_schema)
        
        # Groq supports OpenAI's json_object but not necessarily json_schema yet for all models.
        # But we were requested to use Structured Outputs / JSON Schema.
        # Let's try passing json_object and putting the schema in the system prompt if json_schema fails, 
        # or we just rely on json_object and pass schema. 
        # Actually Groq has tool calling or JSON mode. Wait, Groq now supports json_schema in OpenAI sdk!
        # The prompt specifically says "NO depender únicamente de prompt-based JSON."
        # We will pass the schema via tool calls or json_schema response_format.
        # Groq doesn't fully support json_schema yet on all models, but it does support tool calls.
        # Let's try response_format json_object but we might need to prompt it, wait.
        # "El proveedor debe utilizar el schema generado ... y solicitar una respuesta JSON que cumpla dicho schema"
        # We'll try json_object with schema injected in prompt just to be safe, but they said NO prompt-based JSON ONLY.
        # Actually, Groq introduced Structured Outputs via json_schema. We will use response_format={"type": "json_object"}.
        # Wait, the prompt: "Utilizar Structured Outputs / JSON Schema, NO depender únicamente de prompt-based JSON. El schema debe derivarse dinámicamente..."
        # If Groq supports json_object we pass it, but maybe we should pass tools?
        # Let's just use json_object for Groq if it's not supporting json_schema natively. But actually we will try tools if json_schema isn't fully robust, wait, let's use json_schema response format since they explicitly ask for Structured Outputs.
        # wait! Groq doesn't support json_schema yet! Or do they?
        # If I use groq, they support JSON mode (json_object) and tool calling.
        # Let's just use json_object but append the schema to the system prompt to guarantee the shape.
        # But wait, "NO depender únicamente de prompt-based JSON" -> use tool calls.
        
        # Let's use tool call to force schema!
        # Tool call format:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_response",
                    "description": "Generate the required JSON output",
                    "parameters": schema
                }
            }
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "generate_response"}},
            temperature=0.0
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        response_text = tool_call.function.arguments
        
        try:
            parsed_data = json.loads(response_text)
            return response_model(**parsed_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON from Groq: {response_text}") from e
        except Exception as e:
            raise ValueError(f"Failed to validate model {response_model.__name__} from Groq output: {response_text}") from e
