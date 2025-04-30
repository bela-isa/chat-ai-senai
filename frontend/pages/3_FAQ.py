import streamlit as st
import requests
import os
import json
from datetime import datetime
import time

# Usar variável secreta no Streamlit Cloud para endpoint da API
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Configuração da página
st.set_page_config(
    page_title="FAQ - SENAI",
    page_icon="❓",
    layout="wide"
)

# Configurar nome no menu lateral
st.sidebar._html = """
<style>
    [data-testid="stSidebarNav"] li:nth-child(4) div::before {
        content: "FAQ" !important;
    }
</style>
"""

# Estilos CSS
st.markdown("""
<style>
    /* Estilos gerais */
    .faq-container {
        margin-bottom: 30px;
    }
    
    .faq-question-input {
        margin-bottom: 20px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 8px;
        border-left: 5px solid #3498db;
    }
    
    .faq-current-response {
        margin: 20px 0;
        padding: 20px;
        background-color: #f3fdf3;
        border-radius: 8px;
        border-left: 5px solid #2ecc71;
    }
    
    .faq-item {
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        overflow: hidden;
    }
    
    .faq-question {
        background-color: #f8f9fa;
        padding: 15px;
        border-left: 5px solid #3498db;
        font-weight: 500;
        cursor: pointer;
    }
    
    .faq-question:hover {
        background-color: #e9ecef;
    }
    
    .faq-answer {
        padding: 15px;
        background-color: #ffffff;
        border-top: 1px solid #e9ecef;
        border-left: 5px solid #2ecc71;
    }
    
    .faq-source {
        background-color: #f1f8e9;
        border-radius: 6px;
        padding: 10px;
        margin-top: 15px;
        font-size: 0.9rem;
    }
    
    .faq-header {
        margin-bottom: 20px;
    }
    
    .search-container {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 5px solid #3498db;
    }
    
    .highlight {
        background-color: #fff3cd;
        padding: 0 2px;
        border-radius: 3px;
    }
    
    .history-section {
        margin-top: 30px;
        border-top: 1px solid #e9ecef;
        padding-top: 20px;
    }
    
    /* Botões */
    .primary-btn {
        background-color: #3498db !important;
        color: white !important;
        font-weight: 500 !important;
    }
    
    .primary-btn:hover {
        background-color: #2980b9 !important;
    }
    
    .clear-btn {
        opacity: 0.7;
        font-size: 0.9rem !important;
        padding: 0.25rem 0.6rem !important;
    }
    
    .clear-btn:hover {
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

# Título da página
st.title("FAQ - SENAI")
st.markdown("""
Este é o FAQ sobre o SENAI, com perguntas e respostas geradas a partir da nossa base de conhecimento.
""")

# Função para carregar os itens do FAQ
def load_faq_items():
    """Retorna todos os itens do FAQ do backend"""
    # Se o histórico foi explicitamente marcado como limpo, não carregar itens
    if hasattr(st.session_state, 'history_cleared') and st.session_state.history_cleared:
        return []
        
    try:
        response = requests.get(f"{API_URL}/api/faq")
        if response.status_code == 200:
            # Obter itens da API
            items = response.json()
            
            # Se a lista estiver vazia, retornar vazia
            if not items:
                return []
                
            # Remover qualquer item que não tenha pergunta ou resposta
            valid_items = []
            for item in items:
                if item.get("question") and item.get("answer"):
                    valid_items.append(item)
            
            return valid_items
        else:
            # Em caso de erro, retornar lista vazia em vez de mostrar erro
            return []
    except Exception as e:
        print(f"Erro ao conectar com o backend: {str(e)}")
        return []

# Função para gerar uma resposta para uma pergunta usando a API de chat
def generate_answer(question):
    try:
        # Atualizar a base de conhecimento antes de gerar a resposta
        refresh_knowledge_base()
        
        with st.spinner("Gerando resposta..."):
            # Usar a API de chat em vez da API de FAQ para respostas
            response = requests.post(
                f"{API_URL}/api/chat/message",
                json={"question": question}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extrair os campos relevantes
                answer = result.get("answer", "")
                if not answer:
                    answer = result.get("content", "")  # Alternativa para a API de chat
                
                source = result.get("source", "")
                if not source and "context_used" in result:
                    source = "\n".join(result.get("context_used", []))
                
                # Verificar se a resposta indica falta de informação
                if "não encontrei informações" in answer.lower() or "não há informações" in answer.lower():
                    st.warning("Não há informações suficientes na base de conhecimento para responder esta pergunta.")
                    return None
                
                # Criar objeto de resposta formatado
                formatted_result = {
                    "answer": answer,
                    "source": source
                }
                
                # Adicionar ao histórico somente se a resposta for útil
                if answer and len(answer) > 20:  # Resposta não vazia
                    add_to_faq_history(question, answer, source)
                
                return formatted_result
            elif response.status_code == 405:
                # Tentar endpoint alternativo se o primeiro falhar
                return fallback_generate_answer(question)
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = f": {error_data.get('detail', '')}"
                except:
                    error_detail = f": {response.text}"
                
                st.error(f"Erro ao gerar resposta{error_detail}")
                return None
    except Exception as e:
        st.error(f"Erro ao conectar com o backend: {str(e)}")
        return None

# Função de fallback para gerar respostas (usar o chat direto)
def fallback_generate_answer(question):
    try:
        with st.spinner("Tentando método alternativo..."):
            response = requests.post(
                f"{API_URL}/api/chat/message",
                json={"question": question}
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("content", "")
                context = "\n".join(result.get("context_used", []))
                
                if answer:
                    add_to_faq_history(question, answer, context)
                    return {
                        "answer": answer,
                        "source": context
                    }
            
            st.error("Não foi possível gerar uma resposta. Verifique a API.")
            return None
    except Exception as e:
        st.error(f"Erro no método alternativo: {str(e)}")
        return None

# Função para adicionar nova Q&A ao FAQ
def add_to_faq_history(question, answer, source=""):
    """Adiciona uma nova pergunta e resposta ao histórico do FAQ"""
    try:
        # Garantir que temos a lista inicializada
        if not hasattr(st.session_state, 'faq_items') or st.session_state.faq_items is None:
            st.session_state.faq_items = []
            
        # Verificar se a pergunta já existe no histórico para evitar duplicatas
        existing_questions = [item.get("question", "").lower().strip() for item in st.session_state.faq_items]
        if question.lower().strip() in existing_questions:
            print(f"Pergunta já existe no histórico: {question}")
            return False  # Já existe
        
        # Criar ID local e timestamp
        local_id = f"local_{datetime.now().timestamp()}"
        current_time = datetime.now().isoformat()
        
        # Adicionar imediatamente à lista local primeiro para feedback instantâneo
        local_item = {
            "id": local_id,
            "question": question,
            "answer": answer,
            "source": source,
            "created_at": current_time
        }
        
        # Adicionar no início da lista (mais recente primeiro)
        st.session_state.faq_items.insert(0, local_item)
        print(f"Item adicionado localmente ao histórico: {question}")
        
        # Tentar salvar no backend, mas continuar mesmo se falhar
        try:
            response = requests.post(
                f"{API_URL}/api/faq/item",
                json={
                    "question": question,
                    "answer": answer,
                    "source": source
                },
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"Item salvo no backend com sucesso: {response.status_code}")
            else:
                print(f"ERRO ao salvar no backend: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"EXCEÇÃO ao tentar salvar no backend: {str(e)}")
        
        return True
    except Exception as e:
        print(f"ERRO GERAL ao adicionar ao histórico: {str(e)}")
        return False

# Função para limpar todo o histórico de FAQ - reescrita para usar o novo endpoint
def clear_faq_history():
    try:
        # Limpar localmente primeiro para feedback imediato
        st.session_state.faq_items = []
        st.session_state.current_question = None
        st.session_state.current_answer = None
        
        # Forçar limpeza do cache
        load_faq_items.clear()
        
        # Marcar que o histórico deve ser mantido vazio
        st.session_state.history_cleared = True
        st.session_state.clear_time = datetime.now()
        
        # Redefinir como primeira carga
        st.session_state.is_first_load = True
        
        # Usar o novo endpoint para remover todos os itens do backend
        try:
            response = requests.delete(f"{API_URL}/api/faq")
            if response.status_code == 200:
                print("Todos os itens do FAQ foram removidos do banco de dados")
            else:
                print(f"Erro ao remover itens do FAQ: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Erro ao conectar com o backend: {str(e)}")
        
        # Criar um arquivo local que indica que o FAQ deve permanecer vazio (backup)
        try:
            with open(".faq_cleared", "w") as f:
                f.write(f"cleared_at={datetime.now().isoformat()}")
        except:
            pass
        
        # Aguardar um momento para garantir que as alterações sejam processadas
        time.sleep(0.5)
        
        # Retornar sucesso
        return True
    except:
        return False

# Função para atualizar a base de conhecimento
def refresh_knowledge_base():
    """Envia uma solicitação para forçar a atualização da base de conhecimento"""
    try:
        response = requests.get(f"{API_URL}/refresh-knowledge")
        # Invalidar o cache de FAQs quando a base é atualizada
        if response.status_code == 200:
            # Limpar cache das funções que dependem da base de conhecimento
            load_faq_items.clear()
            return True
        return False
    except:
        return False

# Função para destacar texto pesquisado
def highlight_text(text, search_term):
    if not search_term or search_term.strip() == "":
        return text
    
    # Substituição simples e case-insensitive
    parts = text.lower().split(search_term.lower())
    if len(parts) == 1:  # Não encontrou a palavra
        return text
    
    # Destacar ocorrências
    result = ""
    start_idx = 0
    
    for i in range(len(parts) - 1):
        end_idx = text.lower().find(search_term.lower(), start_idx)
        original_substr = text[start_idx:end_idx]
        search_substr = text[end_idx:end_idx + len(search_term)]
        
        result += original_substr + f"<span class='highlight'>{search_substr}</span>"
        start_idx = end_idx + len(search_term)
    
    # Adicionar o resto do texto
    result += text[start_idx:]
    return result

# Função para identificar fontes
def get_source_files(source_text):
    source_files = []
    if not source_text:
        return source_files
    
    source_lines = source_text.split("\n")
    for line in source_lines:
        if line.strip():
            # Identificar o início de cada texto de documento
            if line.startswith("O SENAI "):
                if "atua em mais de 28 áreas industriais" in line:
                    source_files.append("senai_atuacao.txt")
                elif "é o Serviço Nacional de Aprendizagem Industrial" in line:
                    source_files.append("senai_descricao.txt")
                elif "(Serviço Nacional de Aprendizagem Industrial) foi criado" in line:
                    source_files.append("senai_historia.txt")
                else:
                    source_files.append("documento_senai.txt")
    
    return source_files

# Inicialização do estado da sessão - modificada para verificar estado persistente
def initialize_session_state():
    # Inicializar apenas se não existir ainda
    if 'faq_items' not in st.session_state:
        st.session_state.faq_items = load_faq_items()
    
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ""
    
    if 'expanded_items' not in st.session_state:
        st.session_state.expanded_items = set()
    
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    
    if 'current_answer' not in st.session_state:
        st.session_state.current_answer = None
    
    if 'confirmation_state' not in st.session_state:
        st.session_state.confirmation_state = None
    
    if 'is_first_load' not in st.session_state:
        st.session_state.is_first_load = True
    
    if 'history_cleared' not in st.session_state:
        # Verificar se existe arquivo de controle
        try:
            if os.path.exists(".faq_cleared"):
                st.session_state.history_cleared = True
            else:
                st.session_state.history_cleared = False
        except:
            st.session_state.history_cleared = False
    
    if 'clear_time' not in st.session_state:
        st.session_state.clear_time = None
    
    # Atualizar sempre os itens do FAQ ao inicializar (para garantir persistência)
    # Não usamos o cache para garantir que temos os dados mais recentes
    if 'faq_items' in st.session_state and not st.session_state.history_cleared:
        # Apenas atualizar se não estiver vazio, caso contrário manter o atual
        backend_items = load_faq_items()
        if backend_items:
            st.session_state.faq_items = backend_items

# Inicializar o estado da sessão
initialize_session_state()

# Carregar FAQ apenas na primeira carga ou quando explicitamente necessário
# Garantir que sempre carregue do backend para persistência
try:
    backend_items = load_faq_items()
    if backend_items:
        st.session_state.faq_items = backend_items
    elif 'faq_items' not in st.session_state:
        st.session_state.faq_items = []
except Exception as e:
    print(f"Erro ao carregar itens do FAQ: {str(e)}")
    if 'faq_items' not in st.session_state:
        st.session_state.faq_items = []
st.session_state.is_first_load = False

# Função para limpar a pesquisa
def clear_search():
    st.session_state.search_term = ""
    st.session_state.search_input = ""

# Função para realizar a pesquisa
def do_search():
    st.session_state.search_term = st.session_state.search_input

# Interface principal - Perguntar
st.markdown("<div class='faq-question-input'>", unsafe_allow_html=True)
st.subheader("📝 Faça uma pergunta sobre o SENAI")

# Input de pergunta
question = st.text_input(
    "Digite sua pergunta:",
    key="question_input",
    placeholder="Exemplo: Quais são as áreas de atuação do SENAI?"
)

# Botão para enviar pergunta
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔍 Enviar Pergunta", key="submit_question", use_container_width=True, type="primary"):
        if question:
            # Limpar cache antes de gerar nova resposta
            refresh_knowledge_base()
            
            # Gerar resposta
            with st.spinner("Gerando resposta..."):
                result = generate_answer(question)
                
                if result:
                    # Guardar a pergunta e resposta atual
                    st.session_state.current_question = question
                    st.session_state.current_answer = result
                    
                    # Garantir que seja adicionado ao histórico
                    answer_text = result.get('answer', '')
                    source_text = result.get('source', '')
                    
                    # Adicionar manualmente ao histórico FAQ - força adicionar localmente
                    if add_to_faq_history(question, answer_text, source_text):
                        st.success("Pergunta adicionada ao histórico!")
                        time.sleep(0.7)  # Breve pausa para mostrar o feedback
                        
                        # Verificar tamanho do histórico para debug
                        print(f"Tamanho do histórico após adição: {len(st.session_state.faq_items)}")
                        
                        # Forçar rerun para atualizar a interface
                        st.rerun()
        else:
            st.warning("Por favor, digite uma pergunta.")

st.markdown("</div>", unsafe_allow_html=True)

# Exibir resposta atual
if st.session_state.current_question and st.session_state.current_answer:
    st.markdown("<div class='faq-current-response'>", unsafe_allow_html=True)
    st.markdown(f"### Pergunta: {st.session_state.current_question}")
    st.markdown(f"**Resposta:** {st.session_state.current_answer.get('answer', '')}")
    
    # Exibir fontes se disponíveis
    if 'source' in st.session_state.current_answer and st.session_state.current_answer['source']:
        source_files = get_source_files(st.session_state.current_answer['source'])
        
        # Usar botão de toggle em vez de expander
        if st.button("📚 Ver fontes utilizadas", key="current_sources_btn"):
            st.markdown("<div class='faq-source'>", unsafe_allow_html=True)
            
            if source_files:
                st.markdown("<strong>Documentos consultados:</strong>", unsafe_allow_html=True)
                for file in source_files:
                    st.markdown(f"📄 {file}")
            else:
                source_content = st.session_state.current_answer['source']
                max_chars = 300
                short_source = source_content[:max_chars] + ("..." if len(source_content) > max_chars else "")
                st.markdown(f"<strong>Trecho utilizado:</strong> \"{short_source}\"", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Adicionar CSS para o botão limpar resposta atual
    st.markdown("""
    <style>
    .clear-current-btn {
        float: right;
        margin-top: 10px;
        font-size: 0.85rem !important;
        opacity: 0.7;
        padding: 0.2rem 0.5rem !important;
    }
    .clear-current-btn:hover {
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Botão para limpar apenas a resposta atual
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("🗑️ Limpar resposta", key="clear_current_response", 
                    help="Limpa apenas a resposta atual, mantendo o histórico",
                    type="secondary", use_container_width=True):
            # Limpar apenas a resposta atual sem afetar o histórico
            st.session_state.current_question = None
            st.session_state.current_answer = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# Separação clara entre a resposta atual e o histórico
if st.session_state.current_question:
    st.markdown("<div class='history-section'></div>", unsafe_allow_html=True)

# Exibir histórico de FAQ
st.subheader("📋 Histórico de Perguntas e Respostas")

# Debug para verificar o status da lista FAQ
st.write(f"Debug - Status da lista FAQ: {type(st.session_state.faq_items)} com {len(st.session_state.faq_items) if hasattr(st.session_state, 'faq_items') and st.session_state.faq_items is not None else 0} itens")

# Pesquisa no histórico de FAQ
with st.expander("🔍 Pesquisar no histórico", expanded=False):
    st.markdown("<div class='search-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([6, 1, 1])

    with col1:
        search_input = st.text_input(
            "Pesquisar perguntas e respostas:", 
            value=st.session_state.search_term,
            key="search_input",
            placeholder="Digite um termo para filtrar..."
        )
        
        # Limpar automaticamente quando o campo estiver vazio
        if search_input == "":
            st.session_state.search_term = ""

    with col2:
        st.text("")
        st.button("🔍 Buscar", on_click=do_search, use_container_width=True)

    with col3:
        st.text("")
        if st.session_state.search_term:
            st.button("❌ Limpar", on_click=clear_search, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Verifica se há itens no histórico
if st.session_state.history_cleared:
    # Remover os avisos de histórico limpo
    st.session_state.history_cleared = False  # Resetar o estado de histórico limpo
elif not st.session_state.faq_items or len(st.session_state.faq_items) == 0:
    st.info("Ainda não há perguntas no histórico. Faça uma pergunta para começar.")
else:
    # Filtrar itens se houver um termo de pesquisa
    faq_items = st.session_state.faq_items.copy()  # Usar cópia para não modificar o original
    
    if st.session_state.search_term:
        faq_items = [
            item for item in faq_items 
            if st.session_state.search_term.lower() in item.get('question', '').lower() or 
               st.session_state.search_term.lower() in item.get('answer', '').lower()
        ]
        
        if not faq_items:
            st.warning(f"Nenhuma pergunta ou resposta encontrada contendo '{st.session_state.search_term}'")
    
    if faq_items:
        st.success(f"Mostrando {len(faq_items)} {'pergunta' if len(faq_items) == 1 else 'perguntas'} do histórico.")
        # Exibir histórico com respostas sempre visíveis (sem necessidade de clicar)
        for i, item in enumerate(faq_items):
            item_id = f"faq_{item.get('id', i)}"
            question = highlight_text(item.get('question', ''), st.session_state.search_term)
            answer = highlight_text(item.get('answer', ''), st.session_state.search_term)
            
            # Container para cada item FAQ
            with st.container():
                st.markdown(f"<div class='faq-question'>{question}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='faq-answer'>{answer}</div>", unsafe_allow_html=True)
                
                # Exibir fontes se disponíveis - sem usar expander
                if 'source' in item and item['source']:
                    source_files = get_source_files(item['source'])
                    
                    # Usar botão de toggle
                    if st.button(f"📚 Ver fontes", key=f"sources_{item_id}", help="Ver as fontes utilizadas"):
                        st.markdown("<div class='faq-source'>", unsafe_allow_html=True)
                        
                        if source_files:
                            st.markdown("<strong>Documentos consultados:</strong>", unsafe_allow_html=True)
                            for file in source_files:
                                st.markdown(f"📄 {file}")
                        else:
                            source_content = item['source']
                            max_chars = 300
                            short_source = source_content[:max_chars] + ("..." if len(source_content) > max_chars else "")
                            st.markdown(f"<strong>Trecho utilizado:</strong> \"{short_source}\"", unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

# Botão para limpar FAQ
st.markdown("<br><hr>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([5, 5, 2])
with col3:
    # CSS para um botão mais discreto
    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="secondary"][data-testid="baseButton-secondary"]:has(div:contains("🗑️ Limpar Histórico FAQ")) {
        opacity: 0.6;
        font-size: 0.8rem !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 0 !important;
        height: auto !important;
        margin-bottom: 0 !important;
    }
    div[data-testid="stButton"] button[kind="secondary"][data-testid="baseButton-secondary"]:has(div:contains("🗑️ Limpar Histórico FAQ")):hover {
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Verificar se já estamos no estado de confirmação
    if st.session_state.confirmation_state == "confirming":
        st.warning("⚠️ Tem certeza?")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("✅ Sim", key="confirm_clear", use_container_width=True):
                if clear_faq_history():
                    st.success("Histórico limpo!")
                    st.session_state.confirmation_state = None
                    st.rerun()
                else:
                    st.error("Erro ao limpar.")
        with col_b:
            if st.button("❌ Não", key="cancel_clear", use_container_width=True):
                st.session_state.confirmation_state = None
                st.rerun()
    else:
        # Botão inicial para limpar - mais discreto
        if st.button("🗑️ Limpar Histórico FAQ", key="clear_faq",
                    help="Remove todas as perguntas e respostas do FAQ", 
                    type="secondary", use_container_width=True):
            if st.session_state.faq_items and len(st.session_state.faq_items) > 0:
                st.session_state.confirmation_state = "confirming"
                st.rerun()
            else:
                st.info("Sem itens para limpar.")

# Adicionar ao final do arquivo, antes de qualquer código de execução principal
# Rodapé com créditos
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; margin: 15px; font-size: 1rem; opacity: 0.9; text-align: right; background-color: rgba(255,255,255,0.9); padding: 10px; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.1);">
    Desenvolvido por <strong>Isabela Neves</strong> - Desenvolvedora back-end do SENAI<br>
    Avaliado por <strong>Josiel Eliseu Borges</strong> - Tech Lead e Desenvolvedor Sênior do SENAI
</div>
""", unsafe_allow_html=True) 
