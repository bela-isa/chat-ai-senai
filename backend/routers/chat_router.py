from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
import uuid
from datetime import datetime
from models.schemas import QuestionRequest
from db.database import get_db, ChatSession, ChatMessage
from chains.qa_chain import QAChain
from services.openai_service import OpenAIService

router = APIRouter()
qa_chain = QAChain()
openai_service = OpenAIService()

@router.post("/chat/message")
async def send_message(request: QuestionRequest, db: Session = Depends(get_db)):
    """Envia uma mensagem para o chat e retorna a resposta"""
    try:
        # Verificar se existe uma sessão ativa
        session_id = str(uuid.uuid4())
        
        # Criar nova sessão
        chat_session = ChatSession(
            session_id=session_id,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow()
        )
        
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        
        # Salvar a mensagem do usuário
        user_message = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=request.question,
            timestamp=datetime.utcnow()
        )
        
        db.add(user_message)
        db.commit()
        
        # Gerar resposta usando o QA Chain
        answer, context_used, tokens_used = qa_chain.get_answer(request.question)
        
        # Salvar a resposta do assistente
        assistant_message = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=answer,
            context_used=json.dumps(context_used),
            tokens_used=tokens_used,
            timestamp=datetime.utcnow()
        )
        
        db.add(assistant_message)
        db.commit()
        
        return {
            "session_id": session_id,
            "answer": answer,
            "context_used": context_used,
            "tokens_used": tokens_used
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/message/stream")
async def send_message_stream(request: QuestionRequest, db: Session = Depends(get_db)):
    """Envia uma mensagem para o chat e retorna a resposta em streaming"""
    session_id = None
    chat_session = None
    
    try:
        # Gerar session_id e criar nova sessão
        session_id = str(uuid.uuid4())
        
        # Criar nova sessão
        chat_session = ChatSession(
            session_id=session_id,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow()
        )
        
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        
        # Salvar a mensagem do usuário
        user_message = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=request.question,
            timestamp=datetime.utcnow()
        )
        
        db.add(user_message)
        db.commit()
        
        # Buscar documentos relevantes
        relevant_docs = qa_chain.get_relevant_context(request.question)
        context = "\n".join(relevant_docs) if relevant_docs else ""
        
        # Função geradora para streaming da resposta
        async def response_generator():
            # Inicializar variáveis para rastrear a resposta completa
            full_response = ""
            error_occurred = False
            
            try:
                # Enviar um heartbeat inicial para estabelecer a conexão
                yield f"data: {json.dumps({'content': '', 'type': 'heartbeat'})}\n\n"
                
                # Configurar o streaming de resposta
                async for chunk in openai_service.get_streaming_completion(request.question, context):
                    try:
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response += content
                            # Enviar o chunk como um evento SSE
                            yield f"data: {json.dumps({'content': content, 'type': 'content'})}\n\n"
                    except Exception as chunk_error:
                        print(f"Erro ao processar chunk: {str(chunk_error)}")
                        continue  # Continuar para o próximo chunk
                
                # Tentar salvar a resposta no banco de dados
                try:
                    if chat_session and full_response:
                        assistant_message = ChatMessage(
                            session_id=chat_session.id,
                            role="assistant",
                            content=full_response,
                            context_used=json.dumps(relevant_docs),
                            tokens_used=0,  # Temporariamente zero, difícil contar tokens em streaming
                            timestamp=datetime.utcnow()
                        )
                        
                        db.add(assistant_message)
                        db.commit()
                except Exception as db_error:
                    print(f"Erro ao salvar resposta no banco de dados: {str(db_error)}")
                    # Não interromper o fluxo, continuar para enviar a mensagem final
                
                # Enviar mensagem de conclusão
                yield f"data: {json.dumps({'content': '', 'done': True, 'session_id': session_id, 'type': 'complete'})}\n\n"
                
            except Exception as stream_error:
                error_occurred = True
                error_msg = f"Erro durante streaming: {str(stream_error)}"
                print(error_msg)
                
                # Enviar mensagem de erro como evento SSE
                yield f"data: {json.dumps({'error': error_msg, 'type': 'error'})}\n\n"
                
                # Garantir que enviamos uma mensagem de encerramento mesmo em caso de erro
                yield f"data: {json.dumps({'content': '', 'done': True, 'session_id': session_id, 'type': 'complete', 'error': True})}\n\n"
                
            # Garantir que a conexão seja fechada adequadamente
            yield f"data: {json.dumps({'type': 'close'})}\n\n"
        
        # Retornar a resposta de streaming com headers adequados
        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Desativar buffering para nginx
            }
        )
        
    except Exception as e:
        # Tentar fazer rollback se possível
        try:
            if db:
                db.rollback()
        except:
            pass
        
        print(f"Erro na preparação do streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Falha ao iniciar streaming: {str(e)}")

@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Retorna o histórico de mensagens de uma sessão de chat"""
    try:
        # Buscar a sessão
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
            
        # Buscar as mensagens
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.timestamp).all()
        
        result = []
        for msg in messages:
            message_data = {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            
            # Incluir informações adicionais para mensagens do assistente
            if msg.role == "assistant" and msg.context_used:
                message_data["context_used"] = json.loads(msg.context_used)
                message_data["tokens_used"] = msg.tokens_used
                
            result.append(message_data)
        
        return {
            "session_id": session_id,
            "messages": result
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 