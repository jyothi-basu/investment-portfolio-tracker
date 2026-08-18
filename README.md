# Investment Portfolio Tracker

Investment Portfolio Tracker is a Flask-based Python backend project for tracking stock portfolios across multiple demat accounts. Its defining feature is a multi-source, tool-calling AI assistant that combines backend portfolio tools, uploaded-document retrieval, and application-help guidance in a layered application design.

The current implementation includes:

- user registration and login
- portfolio management across multiple demat accounts
- manual stock-price maintenance for currently held stocks
- persistent chat history
- document upload and per-chat indexing
- a tool-calling AI assistant that can answer portfolio, uploaded-document, and app-usage questions

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

- layered Flask backend design
- exact portfolio calculations in a service layer
- authenticated, user-scoped data access
- document ingestion with PDF page-level metadata
- vector search with Chroma
- LangChain tool calling with trusted server-side request context
- user- and chat-scoped document retrieval
- source citations for assistant answers

## Tech Highlights

- Flask routes separated from business rules and repository code
- SQLite-backed relational storage for users, chats, transactions, and documents
- Chroma-backed vector store for uploaded-document retrieval
- OpenAI + LangChain tool-calling assistant
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
| Authentication | Register, log in, session-based protection |
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

- You must log in before using portfolio pages.
- You can only see your own data.
- Stock prices must be entered manually and only for stocks currently held in the portfolio.
- The AI assistant requires `OPENAI_API_KEY` to be set in the environment.
- If you delete a demat account, its transactions are also removed.
- If you enter invalid values, the app will show a validation message.

## Setup

### Tech Stack

- Python 3
- Flask
- SQLite
- Jinja2
- Bootstrap 5
- Vanilla JavaScript
- bcrypt for password hashing
- OpenAI for chat generation
- LangChain tool calling
- Chroma vector storage

### Project Structure

```text
investment_portfolio_tracker/
├── app.py
├── app/
│   ├── __init__.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── app_help.py
│   │   ├── chat.py
│   │   ├── context.py
│   │   ├── orchestrator.py
│   │   ├── prompts.py
│   │   ├── tools.py
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── chunker.py
│   │       ├── embeddings.py
│   │       ├── loader.py
│   │       ├── retriever.py
│   │       ├── validator.py
│   │       └── vector_store.py
│   ├── repository/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── common.py
│   │   └── portfolio.py
│   └── services/
│       ├── __init__.py
│       ├── chat_service.py
│       ├── document_service.py
│       └── portfolio_service.py
├── schema.sql
├── requirements.txt
├── README.md
├── SRS.md
├── portfolio.db
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
3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python app.py
```

5. Open the browser at the local address shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

### Architecture

The project is organized in layers:

- `app/routes/` handles HTTP requests, form handling, and redirects
- `app/services/` handles business rules
- `app/repository/` handles SQLite operations
- `app/ai/` handles prompt templates, trusted assistant context, LangChain tool calling, and RAG helpers
- `schema.sql` defines the database schema
- `app.py` starts the Flask application

The assistant uses a tool-calling flow:

1. The user asks a question in chat.
2. The LLM decides whether it needs portfolio data, uploaded-document evidence, app-help content, or more than one source.
3. The server executes the selected tools with trusted authenticated context.
4. `user_id` and `chat_id` are supplied by the server, not by the model.
5. Uploaded-document retrieval is scoped to the authenticated user and active chat.
6. The tool results are returned to the LLM.
7. The LLM generates the final answer, and the UI renders sources when document evidence is used.

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

For document-specific facts, current tool results are the source of truth. Conversation history can help the model understand follow-up questions, but it is not treated as evidence for uploaded-document answers. If the current retrieved evidence does not support a fact, the assistant should say it cannot be verified from the currently available uploaded documents rather than guessing from earlier chat context.

### Backend Engineering Highlights

This project is a solid example of Python backend work because it demonstrates:

- layered Flask architecture
- service-layer business rules
- exact portfolio calculations
- authenticated data access
- document ingestion and RAG
- trusted tool calling with LLMs
- per-chat source isolation

### Authentication

User passwords are stored securely using bcrypt hashing. Session-based authentication is used, and protected pages require login.

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

- Confirm that `OPENAI_API_KEY` is set
- Check that the selected OpenAI model is valid
- Verify your internet connection

### The assistant gives the wrong kind of answer

- Ask the question more directly
- Upload the relevant document into the same chat
- Make sure the active chat is the one that contains the document evidence
- Remember that app-help, portfolio, and document questions now route through separate tools

## License

This project is licensed under the [MIT License](LICENSE).
