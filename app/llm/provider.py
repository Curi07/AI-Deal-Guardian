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
            data = self.mock_response.pop(0)
        else:
            data = self.mock_response
        return response_model(**data)
