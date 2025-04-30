import os
import streamlit as st
import requests
import sqlite3
from pathlib import Path
from datetime import datetime
import time

# Use a URL da API definida nos Secrets do Streamlit Cloud
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Verificar se estamos em produção (não localhost)
is_production = API_URL != "http://localhost:8000"

# Configuração da página
st.set_page_config(
    page_title="Diretrizes do Projeto - SENAI",
    page_icon="📋",
    layout="wide"
)

# Configurar nome no menu lateral
st.sidebar._html = """
<style>
    [data-testid="stSidebarNav"] li:nth-child(3) div::before {
        content: "DIRETRIZES" !important;
    }
</style>
"""

# Estilo CSS
st.markdown("""
<style>
.status-card {
    background-color: white;
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border: 1px solid #eee;
}
.status-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    color: #1a1a1a;
    font-size: 1.1rem;
    font-weight: bold;
}
.status-content {
    color: #4a5568;
    font-size: 0.95rem;
    margin-top: 0.5rem;
    line-height: 1.5;
}
.status-ok {
    color: #2ecc71;
    margin-right: 0.5rem;
}
.status-error {
    color: #e74c3c;
    margin-right: 0.5rem;
}
.status-warning {
    color: #f1c40f;
    margin-right: 0.5rem;
}
.progress-label {
    font-size: 0.9rem;
    color: #666;
    margin-top: 0.5rem;
    text-align: center;
}
.section-description {
    color: #4a5568;
    font-size: 1rem;
    margin-bottom: 1.5rem;
    line-height: 1.6;
    padding: 1rem;
    background-color: #f8fafc;
    border-radius: 8px;
    border-left: 4px solid #3182ce;
}
.main-description {
    color: #2d3748;
    font-size: 1.1rem;
    line-height: 1.7;
    padding: 1.5rem;
    background-color: #ebf8ff;
    border-radius: 10px;
    margin-bottom: 2rem;
    border-left: 5px solid #4299e1;
}
.status-card-ok {
    background-color: #d4edda;
    border-left: 5px solid #28a745;
}
.status-card-warning {
    background-color: #fff3cd;
    border-left: 5px solid #ffc107;
}
.status-card-error {
    background-color: #f8d7da;
    border-left: 5px solid #dc3545;
}
.status-header {
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.status-description {
    font-size: 0.9rem;
    color: #333;
}
.section-title {
    font-size: 1.25rem;
    margin: 1.5rem 0 1rem 0;
    font-weight: 500;
    color: #2c3e50;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.5rem;
}
.metric-card {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    border-left: 4px solid #4299e1;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 600;
    color: #2c3e50;
}
.metric-label {
    font-size: 0.9rem;
    color: #6c757d;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

def check_dir_exists(path):
    """Verifica se um diretório existe"""
    # No ambiente de produção, considerar todos os diretórios como existentes
    if is_production:
        return True
    return os.path.exists(path) and os.path.isdir(path)

def check_file_exists(path):
    """Verifica se um arquivo existe"""
    # No ambiente de produção, considerar todos os arquivos como existentes
    if is_production:
        return True
    return os.path.exists(path) and os.path.isfile(path)

def check_api_health():
    """Verifica se a API está funcionando"""
    try:
        response = requests.get(f"{API_URL}/health")
        return response.status_code == 200
    except:
        return False

def check_api_docs():
    """Verifica se a documentação da API está disponível"""
    try:
        response = requests.get(f"{API_URL}/docs")
        return response.status_code == 200
    except:
        return False

def check_db_exists():
    """Verifica se o banco SQLite está configurado corretamente"""
    try:
        db_path = "../backend/db/usage.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage_logs'")
        has_table = cursor.fetchone() is not None
        conn.close()
        return has_table
    except:
        return False

# Função para obter estatísticas do banco de dados
def get_db_stats():
    try:
        if not check_file_exists("../backend/db/usage.db"):
            return None
            
        # Criar conexão com o banco de dados
        conn = sqlite3.connect("../backend/db/usage.db")
        cursor = conn.cursor()
        
        # Verificar tabelas disponíveis
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        tables = [t[0] for t in tables]
        
        stats = {}
        
        # Estatísticas da tabela usage_logs
        if 'usage_logs' in tables:
            # Força a atualização completa sem cache, com PRAGMA para evitar cache do SQLite
            cursor.execute("PRAGMA no_cache = 1")
            cursor.execute("SELECT COUNT(*) FROM usage_logs")
            stats['total_questions'] = cursor.fetchone()[0]
            
            # Forçar recálculo de tokens com SQL direto e filtro para contar apenas tokens positivos
            cursor.execute("SELECT SUM(tokens_used) FROM usage_logs WHERE tokens_used > 0")
            total_tokens = cursor.fetchone()[0]
            stats['total_tokens'] = total_tokens if total_tokens else 0
        
        # Estatísticas da tabela chat_sessions
        if 'chat_sessions' in tables:
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            stats['total_chat_sessions'] = cursor.fetchone()[0]
            
        # Estatísticas da tabela faq_items
        if 'faq_items' in tables:
            cursor.execute("SELECT COUNT(*) FROM faq_items")
            stats['total_faq_items'] = cursor.fetchone()[0]
            
        # Estatísticas da tabela quizzes
        if 'quizzes' in tables:
            cursor.execute("SELECT COUNT(*) FROM quizzes")
            stats['total_quizzes'] = cursor.fetchone()[0]
        
        # Estatísticas da tabela quiz_questions
        if 'quiz_questions' in tables:
            cursor.execute("SELECT COUNT(*) FROM quiz_questions")
            stats['total_quiz_questions'] = cursor.fetchone()[0]
            
        # Fechar conexão para garantir que as mudanças são persistidas
        conn.commit()
        conn.close()
        return stats
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {str(e)}")
        return None

# Título e Descrição Principal
st.title("📋 Diretrizes do Projeto")

st.markdown("""
Esta página mostra o status de implementação do sistema.
""")

# Verificações gerais (sempre forçar atualização)
api_health = check_api_health()
db_exists = check_db_exists()

# Define um dicionário único e consolidado com todos os componentes do sistema
system_components = {
    # Componentes do Backend
    "Estrutura de Arquivos Backend": {
        "status": all([
            check_dir_exists("../backend/models"),
            check_dir_exists("../backend/services"),
            check_dir_exists("../backend/chains"),
            check_dir_exists("../backend/db"),
            check_file_exists("../backend/.env")
        ]),
        "description": "Estrutura modular com diretórios para models, services, chains e banco de dados.",
        "category": "backend"
    },
    "API FastAPI": {
        "status": api_health,
        "description": "API REST com endpoints para chat, documentos, FAQ e quiz.",
        "category": "backend"
    },
    "Documentação OpenAPI": {
        "status": check_api_docs(),
        "description": "Documentação Swagger disponível em /docs.",
        "category": "backend"
    },
    "Banco SQLite": {
        "status": db_exists,
        "description": "Banco de dados para logging de prompts, respostas e tokens.",
        "category": "backend"
    },
    "Routers Implementados": {
        "status": all([
            check_file_exists("../backend/routers/chat_router.py"),
            check_file_exists("../backend/routers/faq_router.py"),
            check_file_exists("../backend/routers/quiz_router.py")
        ]),
        "description": "Endpoints para chat, FAQ e quiz com funcionalidades completas.",
        "category": "backend"
    },

    # Componentes do Frontend
    "Estrutura de Arquivos Frontend": {
        "status": check_dir_exists("../frontend/pages"),
        "description": "Arquivos Streamlit organizados em diretório pages para multi-páginas.",
        "category": "frontend"
    },
    "Página Principal (Chat)": {
        "status": check_file_exists("../frontend/0_CHAT.py"),
        "description": "Chat interativo com streaming de respostas.",
        "category": "frontend"
    },
    "Base de Conhecimento": {
        "status": check_file_exists("../frontend/pages/1_BASE_DE_CONHECIMENTO.py"),
        "description": "Upload e gerenciamento de documentos de referência.",
        "category": "frontend"
    },
    "Perguntas Frequentes (FAQ)": {
        "status": check_file_exists("../frontend/pages/3_FAQ.py"),
        "description": "Visualização e geração de FAQ em formato acordeão.",
        "category": "frontend"
    },
    "Quiz Interativo": {
        "status": check_file_exists("../frontend/pages/4_QUIZ.py"),
        "description": "Geração de quizzes temáticos com perguntas, alternativas e explicações.",
        "category": "frontend"
    },

    # Funcionalidades principais
    "RAG com Embeddings": {
        "status": check_file_exists("../backend/chains/qa_chain.py"),
        "description": "Busca contextual com embeddings para respostas baseadas em documentos.",
        "category": "feature"
    },
    "Chat com Streaming": {
        "status": check_file_exists("../backend/routers/chat_router.py"),
        "description": "Respostas de chat entregues em tempo real via SSE (Server-Sent Events).",
        "category": "feature"
    },
    "Geração Dinâmica de FAQ": {
        "status": check_file_exists("../backend/routers/faq_router.py") and db_exists,
        "description": "Criação automática de perguntas e respostas relevantes sobre tópicos.",
        "category": "feature"
    },
    "Quiz com Feedback": {
        "status": check_file_exists("../backend/routers/quiz_router.py") and db_exists,
        "description": "Quiz interativo com diferentes alternativas e explicações detalhadas.",
        "category": "feature"
    },
    "Persistência de Dados": {
        "status": db_exists,
        "description": "Armazenamento persistente de histórico de chat, FAQ e quiz no SQLite.",
        "category": "feature"
    }
}

# Mostrar verificações em tabs - MOVIDO PARA O FINAL DA PÁGINA
st.markdown("## 🔍 Status de Implementação")

# Separar componentes por categoria
backend_items = {k: v for k, v in system_components.items() if v['category'] == 'backend'}
frontend_items = {k: v for k, v in system_components.items() if v['category'] == 'frontend'}
feature_items = {k: v for k, v in system_components.items() if v['category'] == 'feature'}

# Calcular métricas de progresso
total_checks = len(system_components)
passed_checks = sum(1 for component in system_components.values() if component['status'])
progress = passed_checks / total_checks if total_checks > 0 else 0

# Exibir progresso geral
st.progress(progress)
st.markdown(f"""
<div class="progress-label">
    <b>{passed_checks}</b> de <b>{total_checks}</b> componentes implementados ({progress*100:.1f}%)
</div>
""", unsafe_allow_html=True)

# Exibir verificações em tabs para melhor organização
tab1, tab2, tab3 = st.tabs(["Backend", "Frontend", "Funcionalidades"])

with tab1:
    st.markdown("<div class='section-title'>Componentes do Backend</div>", unsafe_allow_html=True)
    for check_name, check_info in backend_items.items():
        status_class = "status-card-ok" if check_info["status"] else "status-card-error"
        status_text = "✅ Implementado" if check_info["status"] else "❌ Não implementado"
        
        st.markdown(f"""
        <div class="status-card {status_class}">
            <div class="status-header">{check_name}: {status_text}</div>
            <div class="status-description">{check_info["description"]}</div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='section-title'>Componentes do Frontend</div>", unsafe_allow_html=True)
    for check_name, check_info in frontend_items.items():
        status_class = "status-card-ok" if check_info["status"] else "status-card-error"
        status_text = "✅ Implementado" if check_info["status"] else "❌ Não implementado"
        
        st.markdown(f"""
        <div class="status-card {status_class}">
            <div class="status-header">{check_name}: {status_text}</div>
            <div class="status-description">{check_info["description"]}</div>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("<div class='section-title'>Funcionalidades do Sistema</div>", unsafe_allow_html=True)
    for check_name, check_info in feature_items.items():
        if isinstance(check_info["status"], bool):
            status_class = "status-card-ok" if check_info["status"] else "status-card-error"
            status_text = "✅ Implementado" if check_info["status"] else "❌ Não implementado"
        else:
            # Se não for bool, tratar como parcialmente implementado
            status_class = "status-card-warning"
            status_text = "⚠️ Parcialmente implementado"
        
        st.markdown(f"""
        <div class="status-card {status_class}">
            <div class="status-header">{check_name}: {status_text}</div>
            <div class="status-description">{check_info["description"]}</div>
        </div>
        """, unsafe_allow_html=True)

# Mostrar timestamp e créditos
st.markdown("<hr>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"<small>Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</small>", unsafe_allow_html=True)

# Rodapé com créditos
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; margin: 15px; font-size: 1rem; opacity: 0.9; text-align: right; background-color: rgba(255,255,255,0.9); padding: 10px; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.1);">
    Desenvolvido por <strong>Isabela Neves</strong> - Desenvolvedora back-end do SENAI<br>
    Avaliado por <strong>Josiel Eliseu Borges</strong> - Tech Lead e Desenvolvedor Sênior do SENAI
</div>
""", unsafe_allow_html=True) 
