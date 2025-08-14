import os
from abc import ABC, abstractmethod
from langchain.chat_models import init_chat_model
from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer
from langchain_google_genai import ChatGoogleGenerativeAI

# --- LLM Client Abstraction ---
class LLMClient(ABC):
    @abstractmethod
    def invoke(self, messages: list) -> str:
        """Send chat messages and return the assistant reply"""
        pass

# --- Google Gemini Implementation ---
class GoogleLLMClient(LLMClient):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        if model_name is None:
            model_name = "gemini-1.5-flash"
        self.client = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

    def invoke(self, messages: list) -> str:
        response = self.client.invoke(messages)
        return response.content

class OpenAIClient(LLMClient):
    def __init__(self, model_name: str = None, api_key: str = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(temperature=0, openai_api_key=key, model_name=model_name)

    def invoke(self, messages: list) -> str:
        res = self.client.chat(messages=messages)
        return res.choices[0].message.content

# --- Grok API Implementation (placeholder) ---
class GrokClient(LLMClient):
    def __init__(self, endpoint: str = None, api_token: str = None):
        # initialize grok-specific client
        self.endpoint = endpoint or os.getenv("GROK_ENDPOINT")
        self.token = api_token or os.getenv("GROK_API_TOKEN")

    def invoke(self, messages: list) -> str:
        # implement call to Grok API
        raise NotImplementedError("Grok client not implemented yet.")

# --- Qwen API Implementation (placeholder) ---
class QwenClient(LLMClient):
    def __init__(self, model_name: str = "qwen-7b-chat" ):
        # use qwen SDK or API
        self.model = model_name

    def invoke(self, messages: list) -> str:
        # implement call to Qwen
        raise NotImplementedError("Qwen client not implemented yet.")

# --- Factory to select LLMClient based on env/config ---
def get_llm_client(provider: str, **kwargs) -> LLMClient:
    if provider == "google":
        model_name = kwargs.get("model_name", "gemini-1.5-flash")  # <- default fallback
        return GoogleLLMClient(model_name)
    # ... other providers

