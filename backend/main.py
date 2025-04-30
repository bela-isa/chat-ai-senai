from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from models.schemas import QuestionRequest, QuestionResponse, UsageLog
from db.database import get_db, Usage
from chains.qa_chain import QAChain
from routers.document_router import router as document_router
from routers.faq_router import router as faq_router
from routers.quiz_router import router as quiz_router
from routers.chat_router import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "Prova IA Generativa – Backend"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="API para responder perguntas sobre o SENAI usando documentos com RAG"
)

# Configuração de CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, isso deveria ser mais restrito
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adicionar os routers
app.include_router(document_router, tags=["Documents"])
app.include_router(faq_router, prefix="/api", tags=["FAQ"])
app.include_router(quiz_router, prefix="/api", tags=["Quiz"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])

qa_chain = QAChain()

@app.get("/health", tags=["Utils"])
def health_check():
    return {"status": "ok"}

@app.get("/refresh-knowledge", tags=["Utils"])
def refresh_knowledge():
    """Força uma atualização da base de conhecimento"""
    qa_chain._initialize_documents()
    return {"status": "ok", "message": "Base de conhecimento atualizada"}

@app.post("/question", response_model=QuestionResponse, tags=["QA"])
def answer_question(
    question_request: QuestionRequest,
    db: Session = Depends(get_db)
):
    # Gerar resposta
    answer, context_used, tokens_used = qa_chain.get_answer(question_request.question)
    
    # Registrar uso no banco de dados
    usage_log = Usage(
        timestamp=datetime.utcnow(),
        prompt=question_request.question,
        response=answer,
        tokens_used=tokens_used,
        model_name=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
        context_used=json.dumps(context_used)
    )
    db.add(usage_log)
    db.commit()
    
    return QuestionResponse(
        answer=answer,
        context_used=context_used,
        tokens_used=tokens_used
    )
