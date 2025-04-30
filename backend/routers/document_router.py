from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List
from datetime import datetime
import os
import shutil
from services.document_service import DocumentService
# Importar a instância do QAChain para atualizar o conhecimento
from chains.qa_chain import QAChain

router = APIRouter()
document_service = DocumentService()
qa_chain = QAChain()  # Instância para acesso à base de conhecimento

class DocumentCreate(BaseModel):
    filename: str
    content: str

class Document(BaseModel):
    filename: str
    content: str
    added_at: datetime

# Função interna para atualizar a base de conhecimento
def _refresh_knowledge_base():
    """Atualiza a base de conhecimento quando documentos são modificados"""
    try:
        qa_chain._initialize_documents()
        return True
    except Exception as e:
        print(f"Erro ao atualizar a base de conhecimento: {str(e)}")
        return False

@router.get("/documents", response_model=List[Document])
async def get_documents():
    """Retorna todos os documentos disponíveis"""
    try:
        # Forçar recarga dos documentos
        document_service._load_documents()
        
        documents = []
        for filename, content in document_service.documents.items():
            try:
                filepath = os.path.join(document_service.documents_dir, filename)
                if os.path.exists(filepath):
                    added_at = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    documents.append(Document(
                        filename=filename,
                        content=content,
                        added_at=added_at
                    ))
                else:
                    print(f"Arquivo não encontrado: {filepath}")  # Debug
            except Exception as e:
                print(f"Erro ao processar documento {filename}: {str(e)}")  # Debug
                continue
        
        print(f"Total de documentos retornados: {len(documents)}")  # Debug
        return documents
    except Exception as e:
        print(f"Erro ao listar documentos: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents")
async def create_document(document: DocumentCreate):
    """Adiciona um novo documento"""
    try:
        document_service.add_document(document.filename, document.content)
        # Atualizar a base de conhecimento após adicionar documento
        _refresh_knowledge_base()
        return {"message": "Documento adicionado com sucesso"}
    except Exception as e:
        print(f"Erro ao criar documento: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Remove um documento"""
    try:
        filepath = os.path.join(document_service.documents_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Recarregar documentos
            document_service._load_documents()
            # Atualizar a base de conhecimento após excluir documento
            _refresh_knowledge_base()
            return {"message": "Documento removido com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
    except Exception as e:
        print(f"Erro ao excluir documento: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para upload de arquivo
@router.post("/documents/upload")
async def upload_file(file: UploadFile = File(...)):
    """Endpoint para upload de documentos"""
    try:
        # Gerar caminho único para o arquivo
        filepath = os.path.join(document_service.documents_dir, file.filename)
        
        # Remover arquivo existente com o mesmo nome, se houver
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Salvar o arquivo
        with open(filepath, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Processar o conteúdo se necessário (por exemplo, extrair texto de PDFs)
        # Esta parte é simplificada - em um sistema real, você processaria diferentes tipos de arquivo
        
        # Recarregar documentos
        document_service._load_documents()
        
        # Atualizar a base de conhecimento
        _refresh_knowledge_base()
        
        return {"message": "Arquivo enviado com sucesso"}
    except Exception as e:
        print(f"Erro ao fazer upload do arquivo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 