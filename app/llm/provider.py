import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, TypeVar
from pydantic import BaseModel
import openai
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
