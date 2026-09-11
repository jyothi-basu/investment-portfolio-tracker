# Investment Portfolio Tracker

Investment Portfolio Tracker is a FastAPI-based Python backend project for tracking stock portfolios across multiple demat accounts. Its defining feature is a multi-source, tool-calling AI assistant that combines backend portfolio tools, uploaded-document retrieval, and application-help guidance in a layered application design.

The document RAG pipeline is available through two transports:

- the existing FastAPI + LangChain assistant
- a separate STDIO MCP server for Codex CLI and other MCP clients

The current implementation includes:

- user registration and JWT authentication with access and refresh tokens
- portfolio management across multiple demat accounts
- manual stock-price maintenance for currently held stocks
- persistent chat history
- document upload and per-chat indexing
- a tool-calling AI assistant that can answer portfolio, uploaded-document, and app-usage questions
- a provider-aware AI layer that can target OpenAI-compatible backends or Gemini's native SDK through environment settings

This project demonstrates Python backend engineering, database design, and AI orchestration.

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
- rotated refresh tokens stored as hashes in SQLite
- CSRF-protected server-rendered forms
- document ingestion with PDF page-level metadata
- vector search with Chroma
- LangChain tool calling with trusted server-side request context
- user- and chat-scoped document retrieval
- source citations for assistant answers
- a separate STDIO MCP interface that reuses the same RAG pipeline

## Project Evolution

This project started as a Flask-based portfolio tracker during the early stages of the Agentic AI course. As the architecture evolved, the application was migrated to FastAPI while preserving the business, AI, and RAG layers through a layered architecture. Authentication was subsequently migrated to short-lived JWT access tokens with rotating refresh tokens, preparing the project for MCP SSE and LangGraph orchestration.

## Tech Highlights

- FastAPI routers separated from business rules and repository code
- SQLite-backed relational storage for users, chats, transactions, and documents
- Chroma-backed vector store for uploaded-document retrieval
- OpenAI-compatible and Gemini tool-calling assistant support through LangChain
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

### Feature Summary

| Area | Capability |
| --- | --- |
| Authentication | Register, JWT login, access-token renewal, refresh rotation, logout |
| Portfolio | Demat accounts, transactions, holdings, summaries, manual prices |
| Chat | Persistent per-chat conversations |
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
- The MCP server also requires `MCP_USER_ID` and `MCP_CHAT_ID`.
- If you delete a demat account, its transactions are also removed.
- If you enter invalid values, the app will show a validation message.

## Setup

### Tech Stack

- Python 3
- FastAPI
- SQLite
- Jinja2
- Bootstrap 5
- Vanilla JavaScript
- bcrypt for password hashing
- PyJWT for access and refresh token signing
- Provider-aware chat generation and embeddings through LangChain
- Native Gemini SDK support for chat tool calling
- LangChain tool calling
- Chroma vector storage
- MCP Python SDK for the STDIO document-search server

### Project Structure

```text
investment_portfolio_tracker/
├── app/
│   ├── __init__.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── app_help.py
│   │   ├── chat.py
│   │   ├── context.py
│   │   ├── orchestrator.py
│   │   ├── prompts.py
│   │   ├── provider_factory.py
│   │   ├── tools.py
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
│   │   ├── portfolio.py
│   │   └── public.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py
│   ├── repository/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── security/
│   │   ├── __init__.py
│   │   └── jwt.py
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── chat_service.py
│       ├── document_service.py
│       └── portfolio_service.py
├── schema.sql
├── requirements.txt
├── README.md
├── SRS.md
├── portfolio.db
├── mcp_server.py
├── mcp.config.example.json
├── main.py
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── demat_accounts.html
    ├── transactions.html
    ├── stock_prices.html
    ├── holdings.html
    ├── account_summary.html
    └── portfolio_summary.html
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

5. Run the application:

```bash
uvicorn main:app
```

On Linux/macOS, the equivalent is:

```bash
uvicorn main:app
```

6. Open the browser at the local address shown in the terminal, usually:

```text
http://127.0.0.1:8000
```

### MCP Server

The repository also includes a separate STDIO MCP server for document search.

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
export MCP_USER_ID="1"
export MCP_CHAT_ID="5"
```

The MCP server reads these environment variables:

- `EMBEDDINGS_PROVIDER`
- `EMBEDDINGS_MODEL`
- `EMBEDDINGS_API_KEY`
- `EMBEDDINGS_BASE_URL`
- `MCP_USER_ID`
- `MCP_CHAT_ID`

Use `mcp.config.example.json` as a template if you want to connect the server from Codex CLI or another MCP client. Different MCP clients may use different local config file formats or field names, so adapt the example to the client you are using. For Codex CLI on Linux/macOS, a minimal configuration looks like this:

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
        "MCP_USER_ID": "1",
        "MCP_CHAT_ID": "5"
      }
    }
  }
}
```

The committed MCP config file is a template only. Keep real credentials and local IDs in your private `.env` file, and replace the placeholder `cwd` path with your actual repository path before using it.

### Architecture

The project is organized in layers:

- `main.py` starts the FastAPI application
- `app/routes/*.py` handles HTTP requests, form handling, and redirects
- `app/services/` handles business rules
- `app/repository/` handles SQLite operations
- `app/security/` creates and validates JWT access and refresh tokens
- `app/ai/` handles prompt templates, trusted assistant context, LangChain tool calling, and RAG helpers
- `app/mcp/` handles the STDIO MCP document-search server
- `schema.sql` defines the database schema
- `app.py` is no longer used

### AI Provider Architecture

The project separates chat models and embedding models into independent provider factories.

Chat models:

- support OpenAI-compatible chat providers through configuration
- can use OpenAI-compatible endpoints such as OpenAI-style APIs exposed by third-party providers
- continue to use the same tool-calling orchestration and trusted request context

Embedding models:

- support OpenAI-compatible embedding APIs
- support local SentenceTransformer embedding models configured through `EMBEDDINGS_MODEL`

Design principle: chat generation, document embeddings, document relevance validation, and MCP document search all obtain models through the shared provider factory layer, so compatible providers can be swapped through configuration instead of code changes.

The assistant uses a tool-calling flow:

1. The user asks a question in chat.
2. The LLM decides whether it needs portfolio data, uploaded-document evidence, app-help content, or more than one source.
3. The server executes the selected tools with trusted authenticated context.
4. `user_id` and `chat_id` are supplied by the server, not by the model.
5. Uploaded-document retrieval is scoped to the authenticated user and active chat.
6. The tool results are returned to the LLM.
7. The LLM generates the final answer, and the UI renders sources when document evidence is used.

The MCP server follows the same retrieval path for document search, but it reads `MCP_USER_ID` and `MCP_CHAT_ID` from the environment instead of web request context.

### Embedding Provider Compatibility

This project allows you to choose different providers for chat models and embedding models through environment variables.

#### Important

If you change the embedding provider or embedding model after documents have already been indexed, you must rebuild the ChromaDB vector database.

Why?

Embedding vectors generated by different models live in different vector spaces. Existing document vectors cannot be compared reliably with vectors produced by another embedding model.

#### When should you rebuild embeddings?

- Changing `EMBEDDINGS_PROVIDER`
- Changing `EMBEDDINGS_MODEL`
- Switching between cloud and local embedding models

#### What happens if you don't?

Document search may return poor or incorrect results because query embeddings and stored document embeddings were generated by different models.

After changing the embedding configuration, delete the existing ChromaDB collection or re-index your uploaded documents.

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
- the schema stays in `schema.sql`

### Database

The app uses SQLite and creates a local database file named `portfolio.db`.

The main tables are:

- `users`
- `demat_accounts`
- `transactions`
- `stock_prices`
- `chats`
- `chat_messages`
- `documents`

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
- per-chat source isolation

### Authentication

User passwords are hashed with bcrypt. Successful login issues a short-lived JWT access token and a rotating refresh token in HttpOnly cookies. Refresh-token hashes are stored in SQLite for rotation and logout revocation, while protected routes also accept access tokens through the standard Bearer authorization header. Server sessions are retained only for flash messages, CSRF state, and the last selected chat; they are not an authentication source.

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
