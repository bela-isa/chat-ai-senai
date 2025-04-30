import os
import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import mimetypes

# Configurações da API
#API_URL = os.getenv("API_URL", "http://localhost:8000")
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Configuração da página
st.set_page_config(
    page_title="Base de Conhecimento",
    page_icon="📚",
    layout="wide"
)

# Configurar nome no menu lateral
st.sidebar._html = """
<style>
    [data-testid="stSidebarNav"] li:nth-child(2) div::before {
        content: "BASE DE CONHECIMENTO" !important;
    }
</style>
"""

# Estilos CSS
st.markdown("""
<style>
    /* Estilos gerais */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Seções */
    .section {
        margin-bottom: 40px;
        padding: 5px;
    }
    
    /* Área de upload */
    .file-preview {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tabela de documentos */
    .document-table {
        margin-top: 20px;
        margin-bottom: 30px;
    }
    
    .doc-content {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 15px;
        font-family: monospace;
        white-space: pre-wrap;
        overflow-x: auto;
        margin-top: 10px;
        font-size: 0.9em;
        max-height: 300px;
        overflow-y: auto;
    }
    
    /* Mensagem de sucesso */
    .success-message {
        background-color: #d1e7dd;
        color: #0f5132;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# Funções para interagir com a API
def get_documents():
    """Busca a lista de documentos disponíveis na API"""
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            # Validar a estrutura da resposta para evitar o erro TypeError
            response_data = response.json()
            if isinstance(response_data, dict) and "documents" in response_data:
                return response_data["documents"]
            elif isinstance(response_data, list):
                return response_data
            else:
                st.error("Formato de resposta inesperado da API")
                return []
        else:
            st.error(f"Erro ao buscar documentos: {response.status_code}")
            return []
    except requests.RequestException as e:
        st.error(f"Erro de conexão: {str(e)}")
        return []
    except ValueError as e:
        st.error(f"Erro ao processar resposta da API: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Erro inesperado ao buscar documentos: {str(e)}")
        return []

def upload_document(file):
    """Envia um documento para a API"""
    try:
        # Criar formulário multipart/form-data
        files = {"file": (file.name, file.getvalue(), mimetypes.guess_type(file.name)[0])}
        
        # Fazer o upload real
        response = requests.post(f"{API_URL}/documents/upload", files=files)
        
        if response.status_code == 200:
            # Após upload bem-sucedido, atualizar a base de conhecimento
            refresh_knowledge()
            return True, "Arquivo enviado com sucesso!"
        else:
            error_msg = f"Erro ao enviar arquivo: {response.status_code}"
            if response.headers.get('content-type') == 'application/json':
                try:
                    error_detail = response.json().get("detail", "")
                    if error_detail:
                        error_msg = f"Erro: {error_detail}"
                except:
                    pass
            return False, error_msg
    except requests.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"

def refresh_knowledge():
    """Envia uma solicitação para forçar a atualização da base de conhecimento"""
    try:
        response = requests.get(f"{API_URL}/refresh-knowledge")
        return response.status_code == 200
    except:
        return False

def delete_document(document_name):
    """Exclui um documento da base de conhecimento"""
    try:
        response = requests.delete(f"{API_URL}/documents/{document_name}")
        if response.status_code == 200:
            # Atualizar a base de conhecimento após exclusão bem-sucedida
            refresh_knowledge()
            return True, "Documento excluído com sucesso!"
        else:
            return False, f"Erro ao excluir documento: {response.status_code}"
    except requests.RequestException as e:
        return False, f"Erro de conexão: {str(e)}"

def format_file_size(size_bytes):
    """Formata o tamanho do arquivo em bytes para uma string legível"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def get_file_icon(filename):
    """Retorna o emoji apropriado para o tipo de arquivo"""
    return "📝"  # Todos são TXT agora

def get_document_content(doc_name):
    """Busca o conteúdo de um documento específico"""
    for doc in st.session_state.documents:
        if doc.get("filename", "") == doc_name:
            return doc.get("content", "Conteúdo não disponível")
    return "Documento não encontrado"

# Inicialização do estado
if 'documents' not in st.session_state:
    st.session_state.documents = get_documents()
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'uploaded_file_info' not in st.session_state:
    st.session_state.uploaded_file_info = None

# Funções de gerenciamento de estado
def update_document_list():
    st.session_state.documents = get_documents()

def handle_successful_upload(file):
    """Atualizar estado após upload bem-sucedido"""
    st.session_state.upload_success = True
    st.session_state.uploaded_file_info = {
        "name": file.name,
        "size": format_file_size(len(file.getvalue()))
    }
    update_document_list()

# Interface principal
st.title("📚 Base de Conhecimento")
st.markdown("""
Esta página permite gerenciar os documentos utilizados pelo assistente para responder às perguntas.
""")

# Layout com duas colunas
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("Adicionar Arquivo .TXT")
    
    # Mostrar interface de upload apenas se não houver upload em andamento ou recém-concluído
    if not st.session_state.upload_success:
        # Área de upload
        uploaded_file = st.file_uploader(
            "Arraste e solte arquivos aqui",
            type=["txt"],  # Apenas TXT
            label_visibility="collapsed",
            key="file_uploader"
        )
        st.caption("Apenas arquivos .TXT são aceitos")
        
        # Exibir preview e botão de upload quando um arquivo for selecionado
        if uploaded_file:
            file_size = len(uploaded_file.getvalue())
            
            st.markdown('<div class="file-preview">', unsafe_allow_html=True)
            col_icon, col_info = st.columns([1, 5])
            with col_icon:
                st.markdown(f"<h3>📝</h3>", unsafe_allow_html=True)
            with col_info:
                st.markdown(f"**Nome:** {uploaded_file.name}")
                st.markdown(f"**Tamanho:** {format_file_size(file_size)}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Botão de upload
            if st.button("📤 Enviar Documento", use_container_width=True, type="primary"):
                with st.spinner("Enviando documento..."):
                    success, message = upload_document(uploaded_file)
                    
                    if success:
                        handle_successful_upload(uploaded_file)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        # Exibir mensagem de sucesso
        st.success(f"Arquivo enviado com sucesso! O documento '{st.session_state.uploaded_file_info['name']}' ({st.session_state.uploaded_file_info['size']}) foi adicionado à base de conhecimento.")
        
        # Botão para upload de novo arquivo
        if st.button("📄 Adicionar outro arquivo", use_container_width=True):
            st.session_state.upload_success = False
            st.session_state.uploaded_file_info = None
            # Limpar o uploader
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("Arquivos na Base")
    
    # Atualizar lista de documentos dinamicamente
    if st.session_state.upload_success:
        # A lista já foi atualizada no upload bem-sucedido
        pass
    
    # Exibir lista de documentos
    if not st.session_state.documents:
        st.info("Nenhum documento encontrado na base de conhecimento.")
    else:
        # Converter para formato de tabela
        data = []
        for doc in st.session_state.documents:
            doc_name = doc.get("filename", "")
            doc_size = doc.get("size", 0) if "size" in doc else len(doc.get("content", ""))
            doc_date = doc.get("added_at", "")
            
            # Formatação amigável
            file_icon = "📝"  # Todos são TXT
            formatted_size = format_file_size(doc_size)
            formatted_date = doc_date if isinstance(doc_date, str) else (
                doc_date.strftime("%d/%m/%Y %H:%M") if hasattr(doc_date, 'strftime') else str(doc_date)
            )
            
            data.append({
                "Arquivo": f"{file_icon} {doc_name}",
                "Tamanho": formatted_size,
                "Data": formatted_date
            })
        
        # Criar DataFrame
        if data:
            df = pd.DataFrame(data)
            
            # Exibir tabela
            st.dataframe(
                df, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Arquivo": st.column_config.TextColumn("Arquivo", width="large"),
                    "Tamanho": st.column_config.TextColumn("Tamanho", width="small"),
                    "Data": st.column_config.TextColumn("Data de upload", width="medium")
                }
            )
            
            # Mostrar conteúdo dos documentos
            st.subheader("Visualizar Conteúdo")
            for doc in st.session_state.documents:
                doc_name = doc.get("filename", "")
                with st.expander(f"📝 {doc_name}"):
                    content = get_document_content(doc_name)
                    st.markdown(f'<div class="doc-content">{content}</div>', unsafe_allow_html=True)
                    
                    # Botão de exclusão individual
                    if st.button(f"🗑️ Excluir", key=f"del_{doc_name}", help=f"Remover {doc_name} da base de conhecimento"):
                        with st.spinner(f"Excluindo {doc_name}..."):
                            success, message = delete_document(doc_name)
                            if success:
                                st.success(f"Documento excluído com sucesso!")
                                update_document_list()
                                st.rerun()
                            else:
                                st.error(message)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Informações sobre a base de conhecimento
st.markdown("---")
st.markdown("""
### Sobre a Base de Conhecimento

Apenas arquivos .txt são aceitos atualmente. Os documentos aqui adicionados serão automaticamente incorporados à base usada pelo assistente nos módulos de Chat, FAQ e Quiz.
""")

# Rodapé com créditos
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; margin: 15px; font-size: 1rem; opacity: 0.9; text-align: right; background-color: rgba(255,255,255,0.9); padding: 10px; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.1);">
    Desenvolvido por <strong>Isabela Neves</strong> - Desenvolvedora back-end do SENAI<br>
    Avaliado por <strong>Josiel Eliseu Borges</strong> - Tech Lead e Desenvolvedor Sênior do SENAI
</div>
""", unsafe_allow_html=True) 
