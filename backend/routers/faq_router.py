from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from models.schemas import FAQItem, FAQCreateRequest
from db.database import get_db, FAQ
from services.openai_service import OpenAIService
from chains.qa_chain import QAChain

router = APIRouter()
openai_service = OpenAIService()
qa_chain = QAChain()

@router.get("/faq", response_model=List[FAQItem])
async def get_faq(db: Session = Depends(get_db)):
    """Retorna todos os itens do FAQ"""
    try:
        faq_items = db.query(FAQ).order_by(FAQ.created_at.desc()).all()
        result = []
        
        for item in faq_items:
            result.append(FAQItem(
                id=item.id,
                question=item.question,
                answer=item.answer,
                source=item.source,
                created_at=item.created_at
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/faq", response_model=List[FAQItem])
async def generate_faq(request: FAQCreateRequest, db: Session = Depends(get_db)):
    """Gera perguntas e respostas de FAQ baseadas em um tópico e salva no banco de dados"""
    try:
        # Prompt para gerar as perguntas do FAQ
        faq_generation_prompt = f"""
        Gere {request.num_items} perguntas e respostas frequentes sobre "{request.topic}" relacionadas ao SENAI.
        Cada item deve ser informativo e educacional.
        
        É MUITO IMPORTANTE que você formate a resposta EXATAMENTE como JSON no seguinte formato:
        [
            {{
                "question": "Pergunta 1",
                "answer": "Resposta detalhada 1"
            }},
            ...
        ]
        
        NÃO inclua NENHUM texto antes ou depois do JSON.
        NÃO use markdown ou delimitadores de código como ```json ou ```.
        """
        
        # Gerar as perguntas e respostas usando o OpenAI
        faq_json_response, tokens_used = openai_service.get_completion(faq_generation_prompt)
        
        # Processar a resposta JSON
        import json
        import re
        try:
            # Limpar e preparar o texto para parsing JSON
            json_str = faq_json_response.strip()
            
            # Remover marcadores de código (```json, ```) se presentes
            if "```json" in json_str:
                json_str = json_str.split("```json", 1)[1]
            elif "```" in json_str:
                json_str = json_str.split("```", 1)[1]
                
            if json_str.endswith("```"):
                json_str = json_str.rsplit("```", 1)[0]
            
            # Limpeza adicional
            json_str = json_str.strip()
            
            # Tenta fazer o parsing do JSON
            try:
                faq_items_data = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                # Logging do erro para diagnóstico
                print(f"Erro no parsing JSON inicial: {str(json_err)}")
                print(f"Texto recebido: {json_str[:100]}...") # Primeiros 100 caracteres para diagnóstico
                
                # Tentativa de correção: buscar apenas o array JSON válido
                array_pattern = r'\[\s*\{.*\}\s*\]'
                array_match = re.search(array_pattern, json_str, re.DOTALL)
                
                if array_match:
                    try:
                        array_json = array_match.group(0)
                        faq_items_data = json.loads(array_json)
                        print("Parsing de JSON alternativo bem-sucedido")
                    except Exception as e:
                        raise ValueError(f"Falha ao processar JSON mesmo após tentativa de correção: {str(e)}")
                else:
                    raise ValueError(f"Não foi possível encontrar um array JSON válido na resposta")
            
            # Validar o formato
            if not isinstance(faq_items_data, list):
                raise ValueError(f"O formato da resposta não é uma lista: {type(faq_items_data)}")
                
            # Verificar se todos os itens têm os campos necessários
            for i, item in enumerate(faq_items_data):
                required_fields = ["question", "answer"]
                for field in required_fields:
                    if field not in item:
                        raise ValueError(f"Item {i+1} está faltando o campo obrigatório '{field}'")
            
            generated_items = []
            
            for item_data in faq_items_data:
                # Para cada pergunta, buscar documentos relevantes como fonte
                relevant_docs = qa_chain.get_relevant_context(item_data["question"])
                source = "\n".join(relevant_docs) if relevant_docs else "Informação gerada sem fonte específica."
                
                # Criar o item no banco de dados
                db_item = FAQ(
                    question=item_data["question"],
                    answer=item_data["answer"],
                    source=source,
                    created_at=datetime.utcnow()
                )
                
                db.add(db_item)
                db.commit()
                db.refresh(db_item)
                
                # Adicionar à lista de retorno
                generated_items.append(FAQItem(
                    id=db_item.id,
                    question=db_item.question,
                    answer=db_item.answer,
                    source=db_item.source,
                    created_at=db_item.created_at
                ))
            
            return generated_items
            
        except json.JSONDecodeError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Falha ao processar a resposta JSON do modelo: {str(e)}")
        except ValueError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/faq/{faq_id}")
async def delete_faq_item(faq_id: int, db: Session = Depends(get_db)):
    """Remove um item do FAQ"""
    try:
        faq_item = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq_item:
            raise HTTPException(status_code=404, detail="Item de FAQ não encontrado")
            
        db.delete(faq_item)
        db.commit()
        
        return {"message": "Item de FAQ removido com sucesso"}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/faq")
async def delete_all_faq_items(db: Session = Depends(get_db)):
    """Remove todos os itens do FAQ"""
    try:
        # Contar quantos itens serão removidos
        count = db.query(FAQ).count()
        
        # Deletar todos os itens
        db.query(FAQ).delete()
        db.commit()
        
        return {"message": f"Todos os {count} itens do FAQ foram removidos com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 