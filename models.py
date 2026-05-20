from pydantic import BaseModel
from typing import Any, Optional


class Message(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list[Any]] = None
    tool_call_id: Optional[str] = None


class Function(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None


class Tool(BaseModel):
    type: str = "function"
    function: Function


class ChatRequest(BaseModel):
    model: str = "openai/gpt-4o-mini"
    messages: list[Message]
    temperature: Optional[float] = 0
    max_tokens: Optional[int] = None
    tools: Optional[list[Tool]] = None
    tool_choice: Optional[Any] = None
    stream: Optional[bool] = None
