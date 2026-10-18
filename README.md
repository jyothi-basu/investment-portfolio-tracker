# Investment Portfolio Tracker

Investment Portfolio Tracker is a portfolio-quality FastAPI Python backend for tracking stock portfolios across multiple demat accounts. Its defining feature is a multi-source, tool-calling AI assistant that combines backend portfolio tools, uploaded-document retrieval, and application-help guidance in a layered application design.

The document RAG pipeline is available through the web assistant and MCP transports:

- the FastAPI web assistant, orchestrated with LangGraph and provider integrations from LangChain
- a separate STDIO MCP server for Codex CLI and other MCP clients
- a PAT-authenticated Streamable HTTP MCP transport for remote clients

The current implementation includes:

- user registration and JWT authentication with access and refresh tokens
- revocable, Argon2-hashed personal access tokens for MCP clients
- portfolio management across multiple demat accounts
- manual stock-price maintenance for currently held stocks
- persistent chat history
- document upload and per-chat indexing
- a tool-calling AI assistant that can answer portfolio, uploaded-document, and app-usage questions
- a provider-aware AI layer that can target OpenAI-compatible backends or Gemini's native SDK through environment settings

This project demonstrates Python backend engineering, database design, and AI orchestration.

## Portfolio Project Focus

This repository is designed to demonstrate the skills expected from a remote Python backend developer who integrates AI into existing applications:

- production-style FastAPI routing with service and repository boundaries
- secure JWT and PAT authentication with user-scoped access control
- provider-agnostic LLM integration with LangGraph tool orchestration
- reusable AI and MCP tools integrated with existing backend services
- RAG ingestion, retrieval, source citations, and per-chat isolation
- automated pytest coverage for authentication, MCP, AI tools, LangGraph, RAG, and upload boundaries

## What This App Does

The application helps you:

- create an account and log in securely
- manage multiple demat accounts
- record `BUY` and `SELL` stock transactions
- manually update stock prices for stocks currently held in the portfolio
- view current holdings
- view demat account-wise summaries
- view an overall portfolio summary
- use an AI chat assistant for portfolio, uploaded-document, and app-related questions

The app does not connect to any external stock market API. All stock prices are entered by the user.

## Why This Project Stands Out

This project goes beyond CRUD:

- layered FastAPI backend design
- exact portfolio calculations in a service layer
- authenticated, user-scoped data access
- rotated refresh tokens stored as hashes in the configured relational database
- CSRF-protected server-rendered forms
- document ingestion with PDF page-level metadata
- vector search with Chroma
- LangGraph tool-calling orchestration with trusted server-side request context
- a reusable shared registry for seven read-only business tools across AI and MCP
- business-friendly JSON serialization at the AI tool boundary, including normalized transaction and account records
- user- and chat-scoped document retrieval
- source citations for assistant answers
- a separate STDIO MCP interface that reuses the same RAG pipeline
- an authenticated Streamable HTTP MCP interface with user-scoped conversation selection
- a pytest suite covering security boundaries, orchestration contracts, and integration behavior

## Project Evolution

This project started as a Flask-based portfolio tracker during the early stages of the Agentic AI course. As the architecture evolved, the application was migrated to FastAPI while preserving the business, AI, and RAG layers through a layered architecture. Authentication was subsequently migrated to short-lived JWT access tokens with rotating refresh tokens. A PAT-authenticated Streamable HTTP MCP transport was then added without replacing the local STDIO transport, legacy SSE compatibility, or the shared RAG pipeline.

## Tech Highlights

- FastAPI routers separated from business rules and repository code
- SQLAlchemy-backed relational storage for users, chats, transactions, and documents
- Chroma-backed vector store for uploaded-document retrieval
- OpenAI-compatible and Gemini tool-calling assistant support through LangGraph and LangChain provider integrations
- Trusted request context for user and chat ownership
- per-chat document grounding and citations

## User Flow

1. Open the application in your browser.
2. Create a new account using the `Register` page.
3. Log in with your email and password.
4. Add one or more demat accounts such as Zerodha, Groww, Angel One, or ICICI Direct.
5. Add your stock transactions.
6. Update the current stock prices for stocks you currently hold.
7. Open the dashboard to see your holdings and portfolio summary.

### Main Pages

- `Home` - landing page with login and register links
- `Register` - create a new user account
- `Login` - sign in to your account
- `Dashboard` - see total investment, current portfolio value, profit or loss, and holdings
- `Demat Accounts` - add, edit, or delete broker accounts
- `Transactions` - add, edit, or delete buy and sell transactions
- `Stock Prices` - update prices for currently held stocks
- `Holdings` - view current stock holdings
- `Demat Account Wise Summary` - see summary for each demat account
- `Portfolio Summary` - see overall portfolio details
- `Chat` - ask the AI assistant about your portfolio and the app
- `API Tokens` - create and revoke personal access tokens for remote MCP clients

### Feature Summary

| Area | Capability |
| --- | --- |
| Authentication | Register, JWT login, refresh rotation, logout, MCP personal access tokens |
| Portfolio | Demat accounts, transactions, holdings, summaries, manual prices |
| Chat | Persistent conversations, public UUIDs, automatic concise titles |
| Documents | Upload, index, retrieve, delete |
| AI Assistant | Portfolio, document, and app-help tool calling |

### Portfolio Logic

The application uses a simple rule set:

- `Total Investment = total BUY amount - total SELL amount`
- `Current Portfolio Value = current value of remaining holdings`
- `Profit/Loss = Current Portfolio Value - Total Investment`

Example:

- You buy shares worth `100`
- Later you sell shares worth `80`
- Your total investment becomes `20`
- If the remaining holdings are worth `120`, your profit is `100`

### Important Notes for Users

- You must log in before using portfolio pages. Browser authentication uses Secure, HttpOnly JWT cookies.
- You can only see your own data.
- Stock prices must be entered manually and only for stocks currently held in the portfolio.
- The AI assistant uses the provider settings in `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`. Set `LLM_PROVIDER=gemini` to use Gemini's native SDK for tool calling; `LLM_BASE_URL` is not required for Gemini.
- Document embeddings use `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`, and `EMBEDDINGS_API_KEY`.
- The app still accepts the legacy `OPENAI_*` environment variables as fallbacks.
- Local STDIO uses `MCP_CONVERSATION_ID`; remote HTTP MCP uses a personal access token and never accepts internal user or chat IDs.
- If you delete a demat account, its transactions are also removed.
- If you enter invalid values, the app will show a validation message.

## Setup

### Tech Stack

- Python 3
- FastAPI
- PostgreSQL
- Jinja2
- Bootstrap 5
- Vanilla JavaScript
- bcrypt for password hashing
- PyJWT for access and refresh token signing
- Provider-aware chat generation and embeddings through LangChain
- Native Gemini SDK support for chat tool calling
- LangGraph tool-calling orchestration
- Chroma vector storage
- MCP Python SDK for STDIO, Streamable HTTP, and legacy SSE transports
- Argon2 for personal access token hashing
- pytest for automated backend and AI integration testing

### Project Structure

```text
investment_portfolio_tracker/
├── app/
│   ├── __init__.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── app_help.py
│   │   ├── context.py
│   │   ├── langgraph/
│   │   │   ├── __init__.py
│   │   │   ├── edges.py
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   └── state.py
│   │   ├── orchestrator.py
│   │   ├── prompts.py
│   │   ├── provider_factory.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── application.py
│   │   │   ├── common.py
│   │   │   ├── documents.py
│   │   │   ├── portfolio.py
│   │   │   └── registry.py
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── chunker.py
│   │       ├── embeddings.py
│   │       ├── loader.py
│   │       ├── retriever.py
│   │       ├── validator.py
│   │       └── vector_store.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── common.py
│   │   ├── documents.py
│   │   ├── mcp.py
│   │   ├── portfolio.py
│   │   └── public.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── session_manager.py
│   │   ├── sse.py
│   │   ├── streamable_http.py
│   │   └── stdio.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── auth_repository.py
│   │   ├── chat_repository.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── portfolio_repository.py
│   │   ├── serialization.py
│   │   ├── session.py
│   │   └── db.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   └── personal_access_tokens.py
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── chat_service.py
│       ├── chat_title_service.py
│       ├── document_service.py
│       └── portfolio_service.py
├── requirements.txt
├── pytest.ini
├── README.md
├── SRS.md
├── mcp_server.py
├── mcp.config.example.json
├── main.py
├── static/
│   ├── style.css
│   └── script.js
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── demat_accounts.html
│   ├── transactions.html
│   ├── stock_prices.html
│   ├── holdings.html
│   ├── account_summary.html
│   └── portfolio_summary.html
└── tests/
    ├── test_ai_tools_architecture.py
    ├── test_embedding_provider_factory.py
    ├── test_jwt_auth.py
    ├── test_langgraph_architecture.py
    ├── test_mcp_auth.py
    ├── test_mcp_sessions.py
    ├── test_rag_unit.py
    └── test_upload_boundary.py
```

### Setup Instructions

1. Make sure Python 3 is installed.
2. Open a terminal in the project folder.
3. Create `.env` from `.env.example` and replace the placeholder secrets and provider settings. Use separate cryptographically random values for `SECRET_KEY` and `JWT_SECRET_KEY`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

For local HTTP development, keep `JWT_COOKIE_SECURE=false` and `SESSION_COOKIE_SECURE=false`. Set both to `true` when the application is served over HTTPS in production.

Generate each secret independently:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

4. Install the dependencies:

```bash
pip install -r requirements.txt
```

### Database Configuration

The repository uses SQLAlchemy ORM and reads the database connection from `DATABASE_URL`. PostgreSQL is the database currently used by this project, but the repository is not coupled to PostgreSQL. Services, routes, AI tools, and MCP tools do not import a database driver or execute SQL directly.

Create the database before starting the application. SQLAlchemy creates the mapped tables during startup in this commit.

PostgreSQL, the current project setup:

```env
DATABASE_URL=postgresql+psycopg://portfolio_user:password@localhost:5432/portfolio_tracker
```

MySQL, after installing a MySQL SQLAlchemy driver such as `PyMySQL`:

```bash
pip install pymysql
```

```env
DATABASE_URL=mysql+pymysql://portfolio_user:password@localhost:3306/portfolio_tracker
```

SQLite, for a local single-file setup:

```env
DATABASE_URL=sqlite:///./portfolio_tracker.db
```

Changing the URL is normally the only application configuration change. If a future feature requires database-specific SQL, keep that code inside the database/repository boundary rather than changing services or routes. Alembic migrations will be added in a later change; until then, do not use this startup table creation approach for production schema evolution.

For automated tests, create a separate database and set `TEST_DATABASE_URL`. Tests drop and recreate ORM tables, so never point it at the application database:

```env
TEST_DATABASE_URL=postgresql+psycopg://portfolio_user:password@localhost:5432/portfolio_tracker_test
```

5. Run the application:

```bash
uvicorn main:app
```

6. Open the browser at the local address shown in the terminal, usually:

```text
http://127.0.0.1:8000
```

### Run the tests

The automated suite uses `pytest` and covers authentication, repository contracts, database constraints, MCP security, LangGraph orchestration, shared AI tools, embedding-provider selection, RAG boundaries, and document-upload behavior. Set `TEST_DATABASE_URL` before running the complete suite:

```bash
python -m pytest -q
```

The suite intentionally emphasizes framework and architecture behavior rather than coupling every test to a particular database backend.

### MCP Transports

Both MCP transports use the tools registered once in `app/mcp/server.py`. The shared registry exposes the same seven read-only business tools to MCP and the web assistant; MCP additionally exposes the session-only `list_conversations` and `select_conversation` tools.

#### Local STDIO

Run it directly with:

```bash
python mcp_server.py
```

On Linux/macOS, the equivalent is:

```bash
python3 mcp_server.py
```

Set the required environment variables in your shell before starting the server:

```bash
export EMBEDDINGS_PROVIDER="openai"
export EMBEDDINGS_MODEL="text-embedding-3-small"
export EMBEDDINGS_API_KEY="your_api_key_here"
export MCP_CONVERSATION_ID="replace-with-a-conversation-uuid"
```

The STDIO transport reads these environment variables:

- `EMBEDDINGS_PROVIDER`
- `EMBEDDINGS_MODEL`
- `EMBEDDINGS_API_KEY`
- `EMBEDDINGS_BASE_URL`
- `MCP_CONVERSATION_ID`

STDIO clients use client-specific command configuration. A generic local example is:

```json
{
  "mcpServers": {
    "investment-portfolio-tracker-rag": {
      "command": "./venv/bin/python",
      "args": ["mcp_server.py"],
      "cwd": "/home/you/investment_portfolio_tracker",
      "env": {
        "EMBEDDINGS_PROVIDER": "openai",
        "EMBEDDINGS_MODEL": "text-embedding-3-small",
        "EMBEDDINGS_API_KEY": "your_api_key_here",
        "MCP_CONVERSATION_ID": "replace-with-a-conversation-uuid"
      }
    }
  }
}
```

The committed `mcp.config.example.json` demonstrates the remote Streamable HTTP transport. MCP clients use different configuration formats, so keep credentials in environment variables and adapt the example without committing a PAT.

#### Authenticated Streamable HTTP

Start the FastAPI application normally. It exposes:

- `POST /mcp/sse` for Streamable HTTP initialization and JSON-RPC messages
- `GET /mcp/sse` for Streamable HTTP server events and legacy SSE connections
- `DELETE /mcp/sse` for Streamable HTTP session termination
- `POST /mcp/messages` for backward-compatible legacy SSE messages
- `GET /api/v1/conversations` for user-scoped conversation discovery

For Codex CLI, store the PAT in an environment variable and add the URL-based server:

```bash
export IPT_MCP_PAT="ipt_pat_replace_with_your_token"
codex mcp add investment-portfolio-tracker \
  --url http://127.0.0.1:8000/mcp/sse \
  --bearer-token-env-var IPT_MCP_PAT
```

Equivalent `~/.codex/config.toml`:

```toml
[mcp_servers.investment-portfolio-tracker]
url = "http://127.0.0.1:8000/mcp/sse"
bearer_token_env_var = "IPT_MCP_PAT"
```

Codex treats URL-based MCP servers as Streamable HTTP. Other clients may require an explicit `transport = "streamable_http"` field, as shown in `mcp.config.example.json`.

Remote MCP requests use `Authorization: Bearer ipt_pat_...`. Create, inspect, and revoke PATs through the JWT-authenticated endpoints:

- `POST /api/v1/personal-access-tokens`
- `GET /api/v1/personal-access-tokens`
- `DELETE /api/v1/personal-access-tokens/{token_id}`

Browser users can manage the same credentials from `API Tokens` in the authenticated navigation, served at `/settings/personal-access-tokens`. The create response displays the raw PAT once. The configured relational database stores only its Argon2 hash; expiry, last use, and revocation are tracked separately. Configure the client to send the same PAT header on both SSE and message requests. Production deployments must use HTTPS and should set `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` to their exact public values.

HTTP MCP sessions are intentionally stored in memory. Run this transport with one application worker; a multi-worker deployment would require a shared session store or sticky routing.

After connecting, list conversations and call `select_conversation` with a public `conversation_id` UUID. Subsequent `search_uploaded_documents(query)` calls use the selected conversation automatically. Internal integer chat IDs and user IDs are never MCP tool arguments or API response identifiers.

### Architecture

The project is organized in layers:

- `main.py` starts the FastAPI application
- `app/routes/*.py` handles HTTP requests, form handling, and redirects
- `app/services/` handles business rules
- `app/repository/` contains the SQLAlchemy engine, ORM models, domain repositories, and database facade
- `app/security/` validates JWTs and creates, verifies, and revokes MCP PATs
- `app/ai/` contains the LangGraph orchestrator, provider factory, trusted assistant context, shared read-only tool registry, and RAG helpers
- `app/mcp/` shares MCP tools across STDIO and authenticated HTTP transports

### AI Provider Architecture

The project separates chat models and embedding models into independent provider factories.

The production AI path is:

```text
LangGraph → shared tool registry → trusted tool wrappers → services → repository
```

Chat and embedding providers are selected independently. Current support is:

| Capability | Provider value | Client / implementation | Configuration notes |
| --- | --- | --- | --- |
| Chat | `openai` | LangChain `ChatOpenAI` | Uses OpenAI's API; provide `LLM_API_KEY`. |
| Chat | `openai-compatible` | LangChain `ChatOpenAI` | Requires `LLM_BASE_URL`; supports compatible services such as local Ollama during development. |
| Chat | `gemini` | LangChain `ChatGoogleGenerativeAI` | Uses Gemini with `LLM_API_KEY`; no OpenAI-compatible base URL is used. |
| Embeddings | `openai` | LangChain `OpenAIEmbeddings` | Uses OpenAI's embedding API. |
| Embeddings | `openai-compatible` | LangChain `OpenAIEmbeddings` | Requires `EMBEDDINGS_BASE_URL`. |
| Embeddings | `gemini` | LangChain `GoogleGenerativeAIEmbeddings` | Uses Google AI Studio and `gemini-embedding-001`; no base URL is required. |
| Embeddings | `local` | `LocalSentenceTransformerEmbeddings` | Runs a SentenceTransformer model locally; no embedding API key is required. |

For chat, `LLM_API_KEY` falls back to `OPENAI_API_KEY`. For embeddings, the key lookup order is `EMBEDDINGS_API_KEY`, `LLM_API_KEY`, then `OPENAI_API_KEY`. OpenAI-compatible chat and embedding providers require their respective base URL settings. Local Ollama is a development/testing choice, not a separate provider value; it uses `LLM_PROVIDER=openai-compatible`.

LangGraph orchestrates chat-model tool calling with trusted request context.

Design principle: chat generation, document embeddings, document relevance validation, and MCP document search all obtain models through the shared provider factory layer, so compatible providers can be swapped through configuration instead of code changes.

#### Local Ollama for Development

For local development and testing, Ollama can provide the chat model through the existing `openai-compatible` provider. Start Ollama, pull a model that supports tool calling, and configure:

```env
LLM_PROVIDER=openai-compatible
LLM_MODEL=<model name from ollama list>
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
```

The non-empty `LLM_API_KEY` is required by the OpenAI-compatible client; Ollama's local endpoint ignores its value. The application calls the Ollama server, which runs the model locally. This is a development/testing setup only: this project's Render deployment is not configured to reach a developer machine's `localhost` Ollama server. Keep the production LLM configuration pointed at a provider reachable from the deployed application.

The assistant uses a tool-calling flow:

1. The user asks a question in chat.
2. The LLM decides whether it needs portfolio data, uploaded-document evidence, app-help content, or more than one source.
3. The server executes the selected tools with trusted authenticated context.
4. `user_id` and `chat_id` are supplied by the server, not by the model.
5. Uploaded-document retrieval is scoped to the authenticated user and active chat.
6. The tool results are returned to the LLM.
7. The LLM generates the final answer, and the UI renders sources when document evidence is used.

The shared business tool registry currently provides:

- `get_portfolio_summary`
- `get_holdings`
- `get_transactions`
- `get_stock_prices`
- `get_demat_accounts`
- `search_uploaded_documents`
- `get_application_help`

Portfolio services continue to receive explicit `user_id` arguments. AI wrappers obtain identity from trusted assistant context, while MCP adapters obtain identity from authenticated MCP session state. The model never supplies `user_id`, `chat_id`, or `conversation_id`. SQLAlchemy results are normalized into plain business dictionaries before they are serialized for tool consumers.

All MCP transports follow the same retrieval path. Local STDIO resolves `MCP_CONVERSATION_ID` at startup. Streamable HTTP and legacy SSE resolve the authenticated user from a PAT and store the selected public conversation UUID in an in-memory session; ownership is checked before the UUID is mapped to the internal chat ID.

### Embedding Provider Configuration

Select the embedding backend independently with `EMBEDDINGS_PROVIDER`.

#### Gemini Embeddings (Google AI Studio)

Use the native LangChain Google GenAI embedding integration with a Google AI Studio API key:

```env
EMBEDDINGS_PROVIDER=gemini
EMBEDDINGS_MODEL=gemini-embedding-001
EMBEDDINGS_API_KEY=your_google_ai_studio_api_key
EMBEDDINGS_BASE_URL=
```

`EMBEDDINGS_BASE_URL` is not required for Gemini. You may leave `EMBEDDINGS_API_KEY` empty to reuse `LLM_API_KEY` when it contains the same Google AI Studio key. The local SentenceTransformer implementation is not loaded for this provider.

Re-index uploaded documents after switching providers or models. Existing Chroma vectors were generated in the previous model's embedding space and are not interchangeable with the new vectors.

#### Re-indexing after a provider change

If you change the embedding provider or embedding model after documents have already been indexed, you must rebuild the ChromaDB vector database.

Why?

Embedding vectors generated by different models live in different vector spaces. Existing document vectors cannot be compared reliably with vectors produced by another embedding model.

#### When should you rebuild embeddings?

- Changing `EMBEDDINGS_PROVIDER`
- Changing `EMBEDDINGS_MODEL`
- Switching between cloud and local embedding models
- Switching between OpenAI-compatible and Gemini embeddings

#### What happens if you don't?

Document search may return poor or incorrect results because query embeddings and stored document embeddings were generated by different models.

After changing the embedding configuration, delete and recreate the existing ChromaDB collection or re-index your uploaded documents into a fresh collection.

### Local Embeddings

Set `EMBEDDINGS_PROVIDER=local` to use a local SentenceTransformer model instead of a hosted embedding API.

Recommended default:

- `EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5`

Important notes:

- The first run downloads the model weights to your local cache.
- No embedding API key is required for local embeddings.
- You may switch to any compatible SentenceTransformer model by changing `EMBEDDINGS_MODEL` in `.env` without modifying Python code.
- If you later switch embedding provider or embedding model, you must rebuild the ChromaDB vector database and re-index uploaded documents.

### Design Goal

The codebase is intentionally split into clear layers so it is easier to debug, test, and extend:

- request handling stays in `app/routes/`
- business decisions stay in `app/services/`
- database access stays in `app/repository/`
- the schema is defined by SQLAlchemy ORM models; Alembic will manage schema evolution

### Database

The app uses SQLAlchemy and reads its database connection from `DATABASE_URL`. PostgreSQL is the default project deployment choice, while compatible SQLAlchemy URLs can be used for other relational databases.

The main tables are:

- `users`
- `demat_accounts`
- `transactions`
- `stock_prices`
- `chats`
- `chat_messages`
- `documents`

The application creates the mapped tables during startup for now. Alembic will replace startup schema creation once the migration baseline is added.

Uploaded document chunks are stored in Chroma with user/chat ownership metadata and page numbers for PDF documents.

### AI Assistant

The assistant is project-specific and does not provide financial advice.

It can:

- answer app-usage questions using application help content
- answer portfolio questions using exact portfolio calculations from the service layer
- answer uploaded-document questions using RAG retrieval from the current authenticated user and active chat
- combine portfolio and document evidence when both are needed

The assistant does not guess user identity or chat identity. Those values come from trusted server-side request context, so the LLM never controls `user_id` or `chat_id`.

The chat model, embedding model, and document classifier are configured through environment variables. You can use one provider for all of them or split chat and embeddings across two compatible providers. For non-OpenAI services, set the appropriate base URL in the environment so the LangChain OpenAI-compatible clients can reach the right endpoint.

For document-specific facts, current tool results are the source of truth. Conversation history can help the model understand follow-up questions, but it is not treated as evidence for uploaded-document answers. If the current retrieved evidence does not support a fact, the assistant should say it cannot be verified from the currently available uploaded documents rather than guessing from earlier chat context.

### Backend Engineering Highlights

This project is a solid example of Python backend work because it demonstrates:

- layered FastAPI architecture
- service-layer business rules
- exact portfolio calculations
- authenticated data access
- document ingestion and RAG
- trusted tool calling with LLMs
- reusable AI/MCP tool contracts with structured business outputs
- per-chat source isolation
- pytest-based regression and architecture tests

### Authentication

User passwords are hashed with bcrypt. Successful login issues a short-lived JWT access token and a rotating refresh token in HttpOnly cookies. Refresh-token hashes are stored in the configured relational database for rotation and logout revocation, while protected routes also accept access tokens through the standard Bearer authorization header. Server sessions are retained only for flash messages, CSRF state, and the last selected chat; they are not an authentication source.

MCP HTTP authentication is intentionally separate from browser JWT authentication. MCP clients use revocable personal access tokens with an `ipt_pat_` prefix. Raw PATs are shown only at creation, only Argon2 hashes are persisted, and expired or revoked tokens are rejected. Transport session state is process-local and is removed when the client terminates or disconnects.

### Validation Rules

The app currently validates:

- username is required
- email is required and must be unique
- password must be at least 8 characters
- broker name is required
- stock symbol is required
- transaction type must be `BUY` or `SELL`
- quantity must be greater than zero
- price per share must be greater than zero
- current stock price must be greater than zero

### Accessibility Notes

The UI follows basic accessibility practices:

- labels are associated with form controls
- pages use semantic structure
- tables are used for tabular data
- the interface is keyboard-friendly
- Bootstrap is used for responsive layout support

## Troubleshooting

### The app does not start

- Confirm that Python is installed
- Install dependencies again with `pip install -r requirements.txt`
- Check for errors in the terminal

### Registration fails

- Make sure the email is not already used
- Make sure the password is at least 8 characters long

### Portfolio numbers look wrong

- Check that transactions were entered correctly
- Confirm that stock prices are updated only for currently held stocks
- Make sure `BUY` and `SELL` quantities are valid

### Chat does not respond

- Confirm that `LLM_API_KEY` is set, or that the legacy `OPENAI_API_KEY` fallback is available
- Check that the selected chat model is valid for the configured provider
- Verify your internet connection

### The assistant gives the wrong kind of answer

- Ask the question more directly
- Upload the relevant document into the same chat
- Make sure the active chat is the one that contains the document evidence
- Remember that app-help, portfolio, and document questions now route through separate tools

## License

This project is licensed under the [MIT License](LICENSE).
