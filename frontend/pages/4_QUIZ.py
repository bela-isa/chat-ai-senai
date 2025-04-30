import streamlit as st
import requests
import os
import json
import random
from datetime import datetime
import time

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Função para atualizar a base de conhecimento
def refresh_knowledge_base():
    """Envia uma solicitação para forçar a atualização da base de conhecimento"""
    try:
        response = requests.get(f"{API_URL}/refresh-knowledge")
        return response.status_code == 200
    except:
        return False

# Configuração da página
st.set_page_config(
    page_title="QUIZ - SENAI",
    page_icon="🧠",
    layout="wide"
)

# Estilo CSS personalizado
st.markdown("""
<style>
.quiz-container {
    background-color: #f8f9fa;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
}

.question-container {
    background-color: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.question-text {
    font-size: 1.2rem;
    font-weight: 500;
    margin-bottom: 1rem;
}

.result-correct {
    background-color: #d4edda;
    color: #155724;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #28a745;
}

.result-incorrect {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #dc3545;
}

.explanation-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
    border: 1px solid #e9ecef;
}

.correct-answer {
    font-weight: 500;
    color: #28a745;
}

.score-container {
    background-color: #e9ecef;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    text-align: center;
    font-size: 1.2rem;
}

.option-button {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 0.5rem;
    padding: 0.8rem;
    margin: 0.5rem 0;
    width: 100%;
    text-align: left;
    transition: all 0.2s ease;
}

.option-button:hover {
    background-color: #e9ecef;
    border-color: #ced4da;
}

.option-selected {
    background-color: #d1ecf1;
    border-color: #bee5eb;
}
</style>
""", unsafe_allow_html=True)

# Título da página
st.title("🧠 QUIZ - Teste seus conhecimentos")
st.markdown("""
Responda a perguntas sobre o SENAI para testar seus conhecimentos. Você pode gerar um novo quiz sobre qualquer tópico relacionado ao SENAI.
""")

# A atualização da base de conhecimento agora ocorre automaticamente após upload

# Inicialização das variáveis de sessão
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'quiz_questions' not in st.session_state:
    st.session_state.quiz_questions = []
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'total_questions' not in st.session_state:
    st.session_state.total_questions = 0
if 'quiz_completed' not in st.session_state:
    st.session_state.quiz_completed = False
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None

# Função para criar um novo quiz
def create_quiz(topic, num_questions):
    try:
        with st.spinner(f"Gerando {num_questions} perguntas sobre '{topic}'..."):
            # Forçar atualização da base de conhecimento antes de gerar o quiz
            refresh_status = refresh_knowledge_base()
            if not refresh_status:
                st.warning("Não foi possível atualizar a base de conhecimento. O quiz pode não incluir os documentos mais recentes.")
            
            # Aguardar um momento para garantir que a base foi atualizada
            time.sleep(1)
            
            response = requests.post(
                f"{API_URL}/api/quiz",
                json={"topic": topic, "num_questions": num_questions}
            )
            
            if response.status_code == 200:
                questions = response.json()
                
                # Randomizar a ordem das opções em cada pergunta
                for q in questions:
                    if 'options' in q:
                        random.shuffle(q['options'])
                
                return questions
            else:
                st.error(f"Erro ao gerar quiz: {response.text}")
                return []
    except Exception as e:
        st.error(f"Erro ao conectar com o backend: {str(e)}")
        return []

# Função para verificar a resposta
def check_answer(question_id, user_answer):
    try:
        response = requests.post(
            f"{API_URL}/api/quiz/answer",
            json={"question_id": question_id, "user_answer": user_answer}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro ao verificar resposta: {response.text}")
            return None
    except Exception as e:
        st.error(f"Erro ao conectar com o backend: {str(e)}")
        return None

# Função para lidar com a resposta do usuário
def handle_answer():
    if st.session_state.selected_option is None:
        st.warning("Por favor, selecione uma resposta.")
        return
    
    current_q = st.session_state.quiz_questions[st.session_state.current_question]
    user_answer = st.session_state.selected_option
    
    # Verificar resposta
    result = check_answer(current_q['id'], user_answer)
    
    if result:
        # Armazenar resposta do usuário
        st.session_state.user_answers[current_q['id']] = {
            'user_answer': user_answer,
            'is_correct': result['is_correct'],
            'explanation': result['explanation'],
            'correct_answer': result['correct_answer']
        }
        
        if result['is_correct']:
            st.session_state.score += 1
        
        # Avançar para a próxima pergunta ou finalizar o quiz
        if st.session_state.current_question < len(st.session_state.quiz_questions) - 1:
            st.session_state.current_question += 1
            st.session_state.selected_option = None
        else:
            st.session_state.quiz_completed = True
            st.session_state.total_questions = len(st.session_state.quiz_questions)
    
    st.rerun()

# Função para exibir resultado da resposta
def display_answer_result(question_id):
    result = st.session_state.user_answers.get(question_id)
    if not result:
        return
    
    if result['is_correct']:
        st.markdown(f"""
        <div class="result-correct">
            <strong>Correto!</strong> Você acertou!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="result-incorrect">
            <strong>Incorreto.</strong> A resposta correta é: <span class="correct-answer">{result['correct_answer']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="explanation-container">
        <strong>Explicação:</strong><br>
        {result['explanation']}
    </div>
    """, unsafe_allow_html=True)

# Função para reiniciar o quiz
def restart_quiz():
    st.session_state.current_question = 0  # Garantir que é um inteiro
    st.session_state.quiz_questions = []
    st.session_state.user_answers = {}
    st.session_state.score = 0
    st.session_state.total_questions = 0
    st.session_state.quiz_completed = False
    st.session_state.selected_option = None
    st.rerun()

# Interface para criar um novo quiz
if not st.session_state.quiz_questions:
    st.markdown("<div class='quiz-container'>", unsafe_allow_html=True)
    
    st.subheader("Gerar novo Quiz")
    st.markdown("Escolha um tópico para gerar perguntas relacionadas ao SENAI.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        topic = st.text_input("Tópico:", placeholder="Ex: História do SENAI")
    
    with col2:
        num_questions = st.number_input("Número de perguntas:", min_value=3, max_value=10, value=5)
    
    if st.button("Gerar Quiz", use_container_width=True, type="primary"):
        if topic:
            quiz_questions = create_quiz(topic, num_questions)
            if quiz_questions:
                st.session_state.quiz_questions = quiz_questions
                st.session_state.current_question = 0  # Garantir que é um inteiro
                st.rerun()
        else:
            st.warning("Por favor, digite um tópico para o quiz.")
    
    st.markdown("</div>", unsafe_allow_html=True)
else:
    # Exibir quiz em andamento
    if not st.session_state.quiz_completed:
        # Garantir que current_question é um inteiro
        if not isinstance(st.session_state.current_question, int):
            st.session_state.current_question = 0
            
        current_q = st.session_state.quiz_questions[st.session_state.current_question]
        
        st.markdown(f"""
        <div class="question-container">
            <div class="question-text">Pergunta {st.session_state.current_question + 1}/{len(st.session_state.quiz_questions)}: {current_q['question']}</div>
        """, unsafe_allow_html=True)
        
        # Exibir opções como botões
        for i, option in enumerate(current_q.get('options', [])):
            selected = st.session_state.selected_option == option
            button_class = "option-button option-selected" if selected else "option-button"
            
            if st.button(option, key=f"option_{i}", use_container_width=True, 
                        help="Clique para selecionar esta resposta"):
                st.session_state.selected_option = option
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Se já respondeu a pergunta atual
        if current_q['id'] in st.session_state.user_answers:
            display_answer_result(current_q['id'])
            
            col1, col2 = st.columns([1, 1])
            with col2:
                if st.session_state.current_question < len(st.session_state.quiz_questions) - 1:
                    if st.button("Próxima Pergunta", use_container_width=True):
                        st.session_state.current_question += 1
                        st.session_state.selected_option = None
                        st.rerun()
                else:
                    if st.button("Finalizar Quiz", use_container_width=True, type="primary"):
                        st.session_state.quiz_completed = True
                        st.session_state.total_questions = len(st.session_state.quiz_questions)
                        st.rerun()
        else:
            # Botão para confirmar resposta
            if st.session_state.selected_option is not None:
                if st.button("Confirmar Resposta", use_container_width=True, type="primary"):
                    handle_answer()
    else:
        # Exibir resultados finais
        st.markdown(f"""
        <div class="score-container">
            Você acertou <strong>{st.session_state.score}</strong> de <strong>{st.session_state.total_questions}</strong> perguntas!
        </div>
        """, unsafe_allow_html=True)
        
        # Exibir todas as perguntas com as respostas corretas
        for i, question in enumerate(st.session_state.quiz_questions):
            result = st.session_state.user_answers.get(question['id'])
            if not result:
                continue
                
            with st.expander(f"Pergunta {i+1}: {question['question']}", expanded=False):
                if result['is_correct']:
                    st.markdown(f"""
                    <div class="result-correct">
                        <strong>Sua resposta:</strong> {result['user_answer']} ✓
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="result-incorrect">
                        <strong>Sua resposta:</strong> {result['user_answer']} ✗<br>
                        <strong>Resposta correta:</strong> {result['correct_answer']}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="explanation-container">
                    <strong>Explicação:</strong><br>
                    {result['explanation']}
                </div>
                """, unsafe_allow_html=True)
        
        # Botão para novo quiz
        if st.button("Iniciar Novo Quiz", use_container_width=True, type="primary"):
            restart_quiz()

# Rodapé com créditos
st.markdown("""
<div style="position: fixed; bottom: 0; right: 0; margin: 15px; font-size: 1rem; opacity: 0.9; text-align: right; background-color: rgba(255,255,255,0.9); padding: 10px; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.1);">
    Desenvolvido por <strong>Isabela Neves</strong> - Desenvolvedora back-end do SENAI<br>
    Avaliado por <strong>Josiel Eliseu Borges</strong> - Tech Lead e Desenvolvedor Sênior do SENAI
</div>
""", unsafe_allow_html=True)