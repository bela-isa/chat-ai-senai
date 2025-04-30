from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Tuple, AsyncGenerator
import httpx

load_dotenv()

class OpenAIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        
        # Configuração do cliente HTTP com proxy se necessário
        http_client = None
        if os.getenv("HTTPS_PROXY"):
            http_client = httpx.Client(proxies={"https": os.getenv("HTTPS_PROXY")})
        
        # Inicialização do cliente com configurações personalizadas
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            timeout=60.0  # Timeout aumentado para documentos grandes
        )
        
        # Para o cliente async usado no streaming
        self.async_client = None
        
        self.model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto usando o modelo configurado"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Erro ao gerar embedding: {str(e)}")
    
    def get_completion(self, prompt: str, context: str = "") -> Tuple[str, int]:
        """Gera uma resposta usando o modelo de chat com base no prompt e contexto"""
        try:
            messages = [
                {"role": "system", "content": "Você é um assistente especializado em responder perguntas sobre o SENAI com precisão e clareza."},
                {"role": "user", "content": f"Use este contexto para responder à pergunta:\n\nContexto: {context}\n\nPergunta: {prompt}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,  # Balanceamento entre criatividade e precisão
                max_tokens=500    # Limite para respostas concisas
            )
            
            return response.choices[0].message.content, response.usage.total_tokens
        except Exception as e:
            raise Exception(f"Erro ao gerar resposta: {str(e)}")
            
    async def get_streaming_completion(self, prompt: str, context: str = "") -> AsyncGenerator:
        """Gera uma resposta usando o modelo de chat com streaming"""
        try:
            # Lazy-loading do cliente assíncrono
            if self.async_client is None:
                from openai import AsyncOpenAI
                
                # Configuração do cliente HTTP com proxy se necessário
                async_http_client = None
                if os.getenv("HTTPS_PROXY"):
                    async_http_client = httpx.AsyncClient(proxies={"https": os.getenv("HTTPS_PROXY")})
                
                self.async_client = AsyncOpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    http_client=async_http_client,
                    timeout=60.0
                )
            
            messages = [
                {"role": "system", "content": "Você é um assistente especializado em responder perguntas sobre o SENAI com precisão e clareza."},
                {"role": "user", "content": f"Use este contexto para responder à pergunta:\n\nContexto: {context}\n\nPergunta: {prompt}"}
            ]
            
            stream = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                stream=True
            )
            
            async for chunk in stream:
                yield chunk
                
        except Exception as e:
            raise Exception(f"Erro ao gerar resposta em streaming: {str(e)}") 