from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json
from models.schemas import QuizQuestion, QuizCreateRequest, QuizSubmitAnswerRequest, QuizAnswerResponse
from db.database import get_db, Quiz, QuizQuestion as DBQuizQuestion
from services.openai_service import OpenAIService

router = APIRouter()
openai_service = OpenAIService()

@router.get("/quiz", response_model=List[QuizQuestion])
async def get_quizzes(db: Session = Depends(get_db)):
    """Retorna todos os quizzes disponíveis"""
    try:
        # Buscar as perguntas mais recentes, agrupadas por quiz
        quiz_questions = db.query(DBQuizQuestion).all()
        
        result = []
        for question in quiz_questions:
            result.append(QuizQuestion(
                id=question.id,
                question=question.question,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                options=question.get_options()
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz", response_model=List[QuizQuestion])
async def create_quiz(request: QuizCreateRequest, db: Session = Depends(get_db)):
    """Cria um novo quiz baseado em um tópico"""
    try:
        # Criar o quiz no banco de dados
        new_quiz = Quiz(
            topic=request.topic,
            created_at=datetime.utcnow()
        )
        
        db.add(new_quiz)
        db.commit()
        db.refresh(new_quiz)
        
        # Gerar as perguntas do quiz usando o OpenAI
        quiz_generation_prompt = f"""
        Crie exatamente {request.num_questions} perguntas para um quiz sobre "{request.topic}" relacionado ao SENAI.
        
        Para cada pergunta, você DEVE fornecer:
        1. A pergunta em formato claro
        2. A resposta correta
        3. Três alternativas incorretas
        4. Uma explicação detalhada sobre por que a resposta correta está correta
        
        IMPORTANTE: Sua resposta deve ser um JSON válido e DEVE seguir EXATAMENTE este formato:
        [
            {{
                "question": "Pergunta 1",
                "correct_answer": "Resposta correta",
                "options": ["Resposta correta", "Alternativa incorreta 1", "Alternativa incorreta 2", "Alternativa incorreta 3"],
                "explanation": "Explicação detalhada sobre por que a resposta está correta"
            }},
            ...
        ]
        
        Certifique-se de que o JSON seja válido, com todas as chaves entre aspas duplas e valores string também entre aspas duplas.
        Não inclua nenhum texto antes ou depois do JSON.
        """
        
        # Gerar as perguntas e respostas
        quiz_json_response, tokens_used = openai_service.get_completion(quiz_generation_prompt)
        
        # Processar a resposta JSON
        try:
            # Limpar e preparar o texto para parsing JSON
            json_str = quiz_json_response.strip()
            
            # Remover marcadores de código se presentes
            if "```json" in json_str:
                json_str = json_str.split("```json", 1)[1]
            if "```" in json_str:
                json_str = json_str.split("```", 1)[0]
            
            # Limpeza adicional
            json_str = json_str.strip()
            
            # Tenta fazer o parsing do JSON, com fallback para um método mais robusto
            try:
                questions_data = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                # Logging do erro para diagnóstico
                print(f"Erro no parsing JSON inicial: {str(json_err)}")
                print(f"Texto recebido: {json_str[:100]}...") # Primeiros 100 caracteres para diagnóstico
                
                # Tentativa de correção: buscar apenas o array JSON válido
                import re
                array_pattern = r'\[\s*\{.*\}\s*\]'
                array_match = re.search(array_pattern, json_str, re.DOTALL)
                
                if array_match:
                    try:
                        array_json = array_match.group(0)
                        questions_data = json.loads(array_json)
                        print("Parsing de JSON alternativo bem-sucedido")
                    except:
                        raise ValueError(f"Falha ao processar JSON mesmo após tentativa de correção")
                else:
                    raise ValueError(f"Não foi possível encontrar um array JSON válido na resposta")
            
            # Validar o formato
            if not isinstance(questions_data, list):
                raise ValueError(f"O formato da resposta não é uma lista: {type(questions_data)}")
            
            quiz_questions = []
            
            for q_data in questions_data:
                # Verificar se todos os campos necessários estão presentes
                required_fields = ["question", "correct_answer", "explanation", "options"]
                missing_fields = [field for field in required_fields if field not in q_data]
                
                if missing_fields:
                    print(f"Pulando questão incompleta. Campos ausentes: {missing_fields}")
                    continue
                
                # Criar a pergunta no banco de dados
                db_question = DBQuizQuestion(
                    quiz_id=new_quiz.id,
                    question=q_data["question"],
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data["explanation"]
                )
                
                # Definir as opções
                db_question.set_options(q_data["options"])
                
                db.add(db_question)
                db.commit()
                db.refresh(db_question)
                
                # Adicionar à lista de retorno
                quiz_questions.append(QuizQuestion(
                    id=db_question.id,
                    question=db_question.question,
                    correct_answer=db_question.correct_answer,
                    explanation=db_question.explanation,
                    options=db_question.get_options()
                ))
            
            if not quiz_questions:
                raise ValueError("Nenhuma questão válida foi gerada")
            
            return quiz_questions
            
        except json.JSONDecodeError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Falha ao processar a resposta JSON do modelo: {str(e)}")
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/answer", response_model=QuizAnswerResponse)
async def submit_answer(request: QuizSubmitAnswerRequest, db: Session = Depends(get_db)):
    """Verifica se a resposta do usuário está correta"""
    try:
        # Buscar a pergunta
        question = db.query(DBQuizQuestion).filter(DBQuizQuestion.id == request.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Pergunta não encontrada")
        
        # Verificar se a resposta está correta
        is_correct = question.correct_answer.lower() == request.user_answer.lower()
        
        return QuizAnswerResponse(
            is_correct=is_correct,
            explanation=question.explanation,
            correct_answer=question.correct_answer
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quiz/topic/{topic}", response_model=List[QuizQuestion])
async def get_quiz_by_topic(topic: str, db: Session = Depends(get_db)):
    """Busca quizzes por tópico"""
    try:
        # Buscar o quiz mais recente com o tópico especificado
        quiz = db.query(Quiz).filter(Quiz.topic == topic).order_by(Quiz.created_at.desc()).first()
        
        if not quiz:
            return []
            
        # Buscar as perguntas do quiz
        questions = db.query(DBQuizQuestion).filter(DBQuizQuestion.quiz_id == quiz.id).all()
        
        result = []
        for question in questions:
            result.append(QuizQuestion(
                id=question.id,
                question=question.question,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                options=question.get_options()
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 