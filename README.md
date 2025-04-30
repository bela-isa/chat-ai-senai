# Prova IA – Desenvolvedor Back-End IA

O desafio consiste em criar um mini-backend de IA generativa **e** uma UI simples em Streamlit, conforme **user stories** e **corpus** fornecidos por e-mail.

O repositório inicial contém apenas o essencial para que você comece a codar em segundos (FastAPI + Streamlit *Hello, world!*). Cabe a você estruturar, implementar e documentar as demais funcionalidades.

Boa prova 😊  

---

## Estrutura do repositório

| Pasta                  | Descrição                                                                     |
|------------------------|-------------------------------------------------------------------------------|
| **backend/**           | FastAPI básico (`main.py`, health-check)                                      |
| **frontend/**          | `app.py` Streamlit mínimo                                                     |
| **data/corpus/**       | PDFs e DOCXs utilizados no RAG                                                |
| **requirements.txt**   | Adicione as bibliotecas conforme o necessário                                 |
| **README.md**          | <— VOCÊ está lendo — edite apenas a seção **Relatório do candidato** ao final |

---

## Regras de desenvolvimento

1. É permitido adicionar **novas bibliotecas** — basta incluí-las em `requirements.txt` (ou `pyproject.toml` se preferir Poetry).
2. Mantenha o projeto organizado em camadas (API, domínio, infraestrutura, testes).  
   Ex.: `/backend/chains`, `/backend/services`, `/backend/models`.
3. **Obrigatório**  
   - **Logar** prompts, respostas e uso de tokens em SQLite (`backend/db/usage.db`);
   - Commite as bases de dados utilizadas no projeto (em SQlite) 
   - Criar **≥ 4 commits significativos** com mensagens claras;  
4. *Push* direto na `main`/`master` do seu fork — **não** abra *pull request*.  

---

## Versão Python

Recomendado **Python 3.12** (mínimo 3.11).

---

## Configuração local (sem Docker)

### 1 – Clonar o repositório

```bash
git clone {link a ser enviado por e-mail}
cd prova-ia-generativa-backend
```

### 2 – Criar e ativar ambiente virtual

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3 – Instalar dependências

```bash
pip install -r requirements.txt
```

### 4 – Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz (não faça commit!):

```
OPENAI_API_KEY=<fornecida por e-mail>
EMBEDDINGS_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o
```

### 5 – Executar serviços

```bash
# Modo simplificado (recomendado)
python iniciar_aplicacao.py

# Modo manual (dois terminais)
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
streamlit run 0_CHAT.py
```

- **Docs da API**: http://localhost:8000/docs  
- **UI**: http://localhost:8501  

---

## Relatório do candidato

### Funcionalidades implementadas

- **Sistema de RAG completo**: Implementação de retrieval-augmented generation com embeddings para respostas contextuais precisas
- **Interface Streamlit completa**:
  - Chat principal com sugestões e streaming de respostas
  - Base de Conhecimento para upload e gestão de documentos
  - FAQ dinâmico com histórico persistente
  - Quiz interativo com feedback detalhado
  - Diretrizes para monitorar a implementação do sistema
- **Backend robusto**:
  - API REST com endpoints documentados via Swagger
  - Logging de prompts, respostas e tokens em SQLite
  - Estrutura modular (chains, services, models)
  - Tratamento de erros e validações
- **Persistência de dados**:
  - Histórico de FAQ salvo no banco de dados
  - Sessões de chat rastreáveis
  - Upload e armazenamento de documentos
- **Melhorias de UX**:
  - Design responsivo e informações de autoria em todas as páginas
  - Feedback visual durante operações
  - Tratamento de erros amigável

### Correções/melhorias implementadas

- Corrigido erro que impedia a atualização do histórico do FAQ
- Corrigido problemas de persistência no histórico do FAQ após reinicialização
- Melhorado o rodapé com informações de autoria em todas as páginas
- Otimizado o armazenamento e recuperação de perguntas e respostas
- Adicionado .gitignore adequado para arquivos temporários e de configuração

### Novas bibliotecas adicionadas

| Lib | Motivo |
|-----|--------|
| openai==1.12.0 | Integração com API da OpenAI para embeddings e chat completion |
| python-dotenv==1.0.1 | Gerenciamento de variáveis de ambiente |
| sqlalchemy==2.0.27 | ORM para logging em SQLite |
| numpy==1.26.4 | Processamento de embeddings e cálculos de similaridade |
| scikit-learn==1.4.1.post1 | Cálculo de similaridade de cosseno para RAG |
| python-multipart==0.0.9 | Suporte a upload de arquivos no FastAPI |
| httpx==0.24.1 | Cliente HTTP para configuração de proxy |
| streamlit==1.32.2 | Interface do usuário |
| requests==2.31.0 | Comunicação entre frontend e backend |
