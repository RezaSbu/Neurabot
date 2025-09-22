import asyncio
from typing import Dict, Any, List, Optional
from app.openai import chat_stream, get_embedding, get_embeddings
from app.config import settings

class ModelManager:
    def __init__(self):
        self.models = {
            "simple": "gpt-3.5-turbo",
            "medium": "gpt-4o-mini",
            "complex": "gpt-4o",
            "quantized": "gpt-4o-mini"
        }
        self.embedding_models = {
            "default": "text-embedding-3-large",
            "quantized": "text-embedding-3-small"
        }
        self.model_costs = {
            "gpt-3.5-turbo": 0.001,
            "gpt-4o-mini": 0.00015,
            "gpt-4o": 0.01
        }

    def select_model(self, query: str, context_length: int = 0, user_id: str = None) -> str:
        """انتخاب مدل بر اساس پیچیدگی کوئری و زمینه"""
        query_length = len(query.split())
        
        if query_length < 10 and context_length < 1000:
            return self.models["simple"]
        elif query_length < 20 and context_length < 3000:
            return self.models["medium"]
        else:
            return self.models["complex"]

    def select_embedding_model(self, complexity: str = "medium") -> str:
        """انتخاب مدل امبدینگ بر اساس پیچیدگی"""
        return self.embedding_models.get(complexity, self.embedding_models["default"])

    async def get_embedding(self, text: str, complexity: str = "medium") -> List[float]:
        """دریافت امبدینگ با مدل مناسب"""
        model = self.select_embedding_model(complexity)
        return await get_embedding(text, model=model)

    async def get_embeddings_batch(self, texts: List[str], complexity: str = "medium") -> List[List[float]]:
        """دریافت امبدینگ برای چندین متن به صورت همزمان"""
        model = self.select_embedding_model(complexity)
        return await get_embeddings(texts, model=model)

    async def chat_completion(self, messages, model=None, temperature=0.1, **kwargs):
        """تکمیل چت با مدل مناسب"""
        if model is None:
            last_message = messages[-1]["content"]
            context_length = sum(len(msg["content"]) for msg in messages)
            model = self.select_model(last_message, context_length)
        
        return chat_stream(messages=messages, model=model, temperature=temperature, **kwargs)

    async def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """برآورد هزینه استفاده از مدل"""
        if model not in self.model_costs:
            return 0.0
        
        input_cost = (input_tokens / 1000) * self.model_costs[model]
        output_cost = (output_tokens / 1000) * (self.model_costs[model] * 2)
        return input_cost + output_cost

model_manager = ModelManager()