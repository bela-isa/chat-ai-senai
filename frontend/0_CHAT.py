import os
import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configuração de ambiente
#API_URL = os.getenv("API_URL", "http://localhost:8000")
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Configuração da página
st.set_page_config(
    page_title="Chat SENAI",
    page_icon="🤖",
    layout="wide"
)

# Ajuste do menu lateral
st.sidebar._html = """
<style>
    [data-testid="stSidebarNav"] li:nth-child(1) div::before {
        content: "CHAT" !important;
    }
</style>
"""

# Estilos CSS
st.markdown("""
<style>
    /* Estilos gerais */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding-bottom: 80px;
    }
    
    /* Mensagens */
    .message {
        display: flex;
        padding: 15px;
        border-radius: 12px;
        max-width: 90%;
        line-height: 1.5;
    }
    
    .user-message {
        margin-left: auto;
        background-color: #e3f2fd;
        border-left: 4px solid #1976D2;
    }
    
    .assistant-message {
        margin-right: auto;
        background-color: #f3fdf3;
        border-left: 4px solid #43A047;
        width: 90%;
    }
    
    .message-content {
        margin-bottom: 5px;
    }
    
    /* Metadados das mensagens */
    .message-metadata {
        font-size: 0.8rem;
        color: #666;
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(0,0,0,0.05);
    }
    
    .document-reference {
        font-size: 0.75rem;
        margin-top: 5px;
    }
    
    .token-info {
        font-size: 0.7rem;
        text-align: right;
        margin-top: 5px;
        color: #888;
    }
    
    /* Sugestões */
    .suggestions-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 12px;
        margin: 24px 0;
    }
    
    .suggestion-title {
        margin-bottom: 15px;
        font-weight: 500;
    }
    
    /* Botão Limpar */
    .clear-button {
        margin-top: 20px;
        text-align: right;
        padding-right: 20px;
    }
    
    /* Streaming */
    .typing-indicator {
        margin-right: auto;
        background-color: #f5f5f5;
        border-left: 4px solid #9e9e9e;
        padding: 15px;
        border-radius: 12px;
    }
    
    .typing-animation {
        display: inline-block;
    }
    
    .typing-animation span {
        display: inline-block;
        width: 5px;
        height: 5px;
        background-color: #777;
        border-radius: 50%;
        margin: 0 2px;
        animation: typing 1.4s infinite ease-in-out both;
    }
    
    .typing-animation span:nth-child(1) {
        animation-delay: 0s;
    }
    
    .typing-animation span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-animation span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    /* Erros */
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Inicialização do estado de sessão
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'is_typing' not in st.session_state:
    st.session_state.is_typing = False

# Funções auxiliares
def map_document_to_filename(document_text):
    """Mapeia o texto do documento para um nome de arquivo mais amigável."""
    mapping = {
        "O SENAI atua em mais de 28 áreas industriais": "senai_atuacao.txt",
        "O SENAI é o Serviço Nacional de Aprendizagem Industrial": "senai_descricao.txt",
        "O SENAI (Serviço Nacional de Aprendizagem Industrial) foi criado em 1942": "senai_historia.txt"
    }
    
    for prefix, filename in mapping.items():
        if document_text and document_text.startswith(prefix):
            return filename
    
    return "documento.txt"

def check_backend_availability():
    """Verifica se o backend está acessível."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def refresh_knowledge_base():
    """Atualiza a base de conhecimento."""
    try:
        response = requests.get(f"{API_URL}/refresh-knowledge")
        return response.status_code == 200
    except:
        return False

def send_message(question):
    """Enviar mensagem para a API e processar resposta streaming"""
    if not question.strip():
        return False
    
    # Atualizar a base de conhecimento para garantir respostas atualizadas
    refresh_knowledge_base()
    
    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({
        "role": "user", 
        "content": question
    })
    
    # Iniciar o estado de digitação 
    st.session_state.is_typing = True
    
    try:
        # Fazer a chamada de streaming
        payload = {"question": question}
        if st.session_state.session_id:
            payload["session_id"] = st.session_state.session_id
            
        response = requests.post(
            f"{API_URL}/api/chat/message/stream",
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            st.error(f"Erro na comunicação com o servidor: {response.status_code}")
            st.session_state.is_typing = False
            return False
        
        # Processar a resposta em streaming
        full_response = ""
        session_id = st.session_state.session_id
        context_used = []
        tokens_used = 0
        
        # Placeholder para a resposta em streaming
        placeholder = st.empty()
        
        for line in response.iter_lines():
            if not line:
                continue
                
            try:
                line_text = line.decode('utf-8')
                if not line_text.startswith('data: '):
                    continue
                    
                data_json = line_text[6:]
                data = json.loads(data_json)
                
                # Heartbeat ou fechamento
                if data.get('type') == 'heartbeat' or data.get('type') == 'close':
                    continue
                
                # Erro
                if data.get('type') == 'error' or 'error' in data:
                    error_msg = data.get('error', 'Erro desconhecido')
                    placeholder.markdown(f'<div class="error-message">{error_msg}</div>', unsafe_allow_html=True)
                    st.session_state.is_typing = False
                    return False
                
                # Mensagem final
                if data.get('done', False):
                    session_id = data.get('session_id', session_id)
                    context_used = data.get('context_used', context_used)
                    tokens_used = data.get('tokens_used', tokens_used)
                    break
                
                # Conteúdo da resposta
                if 'content' in data:
                    content = data.get('content', '')
                    full_response += content
                    
                    # Atualizar o placeholder com o texto parcial
                    placeholder.markdown(f"""
                    <div class="message assistant-message">
                        <div class="message-content"><strong>Assistente:</strong> {full_response}▌</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                print(f"Erro ao processar streaming: {str(e)}")
                continue
        
        # Limpar o placeholder
        placeholder.empty()
        
        # Salvar a sessão e adicionar a resposta ao histórico
        st.session_state.session_id = session_id
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "context": context_used,
            "tokens": tokens_used
        })
        
        # Finalizar o estado de digitação
        st.session_state.is_typing = False
        return True
        
    except Exception as e:
        st.error(f"Erro ao enviar mensagem: {str(e)}")
        st.session_state.is_typing = False
        return False

# Interface principal
def main():
    # Cabeçalho
    st.title("💬 Chat SENAI")
    st.markdown("Converse com o assistente para obter informações sobre o SENAI.")
    
    # Container principal de chat
    chat_container = st.container()
    with chat_container:
        # Exibir mensagens existentes
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="message user-message">
                    <div class="message-content"><strong>Você:</strong> {message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            elif message["role"] == "assistant":
                # Preparar informações sobre documentos referenciados
                docs_html = ""
                if "context" in message and message["context"]:
                    docs_html = "<div class='document-reference'><strong>Documentos consultados:</strong><br>"
                    for doc in message["context"]:
                        filename = map_document_to_filename(doc)
                        docs_html += f"📄 {filename}<br>"
                    docs_html += "</div>"
                
                # Tokens utilizados - apenas exibir se for maior que zero
                tokens_html = ""
                if message.get("tokens", 0) > 0:
                    tokens_html = f"<div class='token-info'>Tokens: {message.get('tokens', 0)}</div>"
                
                # Exibir a mensagem completa
                with st.container():
                    if docs_html:
                        st.markdown(f"""
                        <div class="message assistant-message">
                            <div class="message-content"><strong>Assistente:</strong> {message["content"]}</div>
                            <div class="message-metadata">
                                {docs_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Versão simplificada sem a div de metadados quando não há documentos
                        st.markdown(f"""
                        <div class="message assistant-message">
                            <div class="message-content"><strong>Assistente:</strong> {message["content"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Exibir indicador de digitação se estiver processando
        if st.session_state.is_typing:
            st.markdown("""
            <div class="message assistant-message">
                <div class="message-content">
                    <strong>Assistente:</strong> ✏️ Assistente está pensando...
                    <div class="typing-animation">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Mostrar sugestões se o histórico estiver vazio
        if not st.session_state.messages:
            st.markdown("<h4 class='suggestion-title'>🤔 Experimente perguntar:</h4>", unsafe_allow_html=True)
            
            sugestoes = [
                "Quais são as áreas de atuação do SENAI?",
                "Como o SENAI contribui para a indústria brasileira?",
                "Que tipos de cursos o SENAI oferece?",
                "Como funciona a pesquisa aplicada no SENAI?",
                "Qual a história do SENAI?",
                "Como o SENAI apoia a inovação industrial?"
            ]
            
            columns = st.columns(3)
            for idx, sugestao in enumerate(sugestoes):
                with columns[idx % 3]:
                    if st.button(sugestao, key=f"sug_{idx}", use_container_width=True):
                        # Processar a sugestão selecionada
                        send_message(sugestao)
                        st.rerun()
    
    # Input de mensagem (fixo na parte inferior)
    message_input = st.chat_input("Digite sua pergunta aqui...", disabled=st.session_state.is_typing)
    if message_input and not st.session_state.is_typing:
        send_message(message_input)
        st.rerun()
    
    # Botão para limpar histórico - mais discreto e sutil
    if st.session_state.messages:
        st.markdown("""
        <style>
        .clear-chat-btn {
            text-align: right;
            margin-top: 20px;
        }
        .clear-chat-btn button {
            font-size: 0.8rem !important;
            padding: 0.2rem 0.5rem !important;
            opacity: 0.65;
            min-height: 0 !important;
            height: auto !important;
        }
        .clear-chat-btn button:hover {
            opacity: 1;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='clear-chat-btn'>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar conversa", key="clear_chat", 
                    help="Remove todo o histórico da conversa",
                    type="secondary"):
            st.session_state.messages = []
            st.session_state.session_id = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Rodapé com créditos
    st.markdown("""
    <div style="position: fixed; bottom: 0; right: 0; margin: 15px; font-size: 1rem; opacity: 0.9; text-align: right; background-color: rgba(255,255,255,0.9); padding: 10px; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.1);">
        Desenvolvido por <strong>Isabela Neves</strong> - Desenvolvedora back-end do SENAI<br>
        Avaliado por <strong>Josiel Eliseu Borges</strong> - Tech Lead e Desenvolvedor Sênior do SENAI
    </div>
    """, unsafe_allow_html=True)

# Executar a aplicação
if __name__ == "__main__":
    main()
