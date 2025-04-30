from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class QuestionRequest(BaseModel):
    question: str
    
class QuestionResponse(BaseModel):
    answer: str
    context_used: List[str]
    tokens_used: int
    
class UsageLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    prompt: str
    response: str
    tokens_used: int
    
    class Config:
        from_attributes = True
        
# Schemas para FAQ
class FAQItem(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str
    source: str
    created_at: Optional[datetime] = None
    
class FAQCreateRequest(BaseModel):
    topic: str
    num_items: int = 5
    
# Schemas para Quiz
class QuizQuestion(BaseModel):
    id: Optional[int] = None
    question: str
    correct_answer: str
    explanation: str
    options: Optional[List[str]] = None
    
class QuizCreateRequest(BaseModel):
    topic: str
    num_questions: int = 5
    
class QuizSubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str
    
class QuizAnswerResponse(BaseModel):
    is_correct: bool
    explanation: str
    correct_answer: str 