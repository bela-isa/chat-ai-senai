from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv
import json
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/usage.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Usage(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    prompt = Column(Text)  # Usando Text para prompts longos
    response = Column(Text)  # Usando Text para respostas longas
    tokens_used = Column(Integer)
    model_name = Column(String)  # Nome do modelo usado
    context_used = Column(Text)  # Documentos usados como contexto
    
    def to_dict(self):
        """Converte o registro para dicionário"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "prompt": self.prompt,
            "response": self.response,
            "tokens_used": self.tokens_used,
            "model_name": self.model_name,
            "context_used": json.loads(self.context_used) if self.context_used else []
        }

# Novas tabelas para chat persistente
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # "user" ou "assistant"
    content = Column(Text)
    context_used = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

# Tabela para FAQ
class FAQ(Base):
    __tablename__ = "faq_items"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    source = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Tabelas para Quiz
class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question = Column(Text)
    correct_answer = Column(Text)
    explanation = Column(Text)
    options = Column(Text)  # JSON string de opções
    
    quiz = relationship("Quiz", back_populates="questions")
    
    def get_options(self):
        """Converte a string JSON em lista de opções"""
        return json.loads(self.options) if self.options else []
    
    def set_options(self, options_list):
        """Converte lista de opções em string JSON"""
        self.options = json.dumps(options_list) if options_list else None

# Criar o banco de dados e as tabelas
Base.metadata.create_all(bind=engine)

def get_db():
    """Fornece uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_usage(db, prompt: str, response: str, tokens: int, model: str, context: list):
    """Registra o uso da API no banco de dados"""
    try:
        usage_log = Usage(
            prompt=prompt,
            response=response,
            tokens_used=tokens,
            model_name=model,
            context_used=json.dumps(context)
        )
        db.add(usage_log)
        db.commit()
        return usage_log
    except Exception as e:
        db.rollback()
        raise Exception(f"Erro ao registrar uso: {str(e)}")

def get_usage_stats(db):
    """Retorna estatísticas de uso"""
    try:
        total_requests = db.query(Usage).count()
        total_tokens = db.query(Usage).with_entities(
            func.sum(Usage.tokens_used)
        ).scalar() or 0
        
        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "average_tokens": total_tokens / total_requests if total_requests > 0 else 0
        }
    except Exception as e:
        raise Exception(f"Erro ao obter estatísticas: {str(e)}") 