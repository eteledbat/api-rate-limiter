from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    """聊天消息模型"""
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    """OpenAI Chat Completion请求模型"""
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None

class Usage(BaseModel):
    """Token使用情况"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class Choice(BaseModel):
    """响应选择"""
    index: int
    message: Message
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    """OpenAI Chat Completion响应模型"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage