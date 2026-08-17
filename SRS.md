# Software Requirements Specification (SRS)

# Project Title

Investment Portfolio Tracker with AI Investment Research Assistant

# Project Overview

Investment Portfolio Tracker is a web-based application for managing stock investments across multiple demat accounts and querying uploaded financial documents through an AI assistant.

The application helps users manage stock investments across multiple demat accounts. Users can record buy and sell transactions, manually maintain prices for currently held stocks, view holdings, analyze account-wise summaries, and view an overall portfolio summary.

The current implementation includes an **AI-powered Investment Research Assistant** built with a constrained tool-calling architecture.

The assistant combines multiple sources of context when needed:

1. The user's recent conversation history.
2. Application-usage/help content.
3. Exact portfolio information from the service layer.
4. Relevant information retrieved from user-uploaded company financial documents using Retrieval-Augmented Generation (RAG).

The project demonstrates the practical use of:

* OpenAI
* LangChain
* Prompt Templates
* Conversation memory
* Document processing
* Text chunking
* Embeddings
* Vector databases
* Semantic retrieval
* AI tools
* Retrieval-Augmented Generation

The application is built using Python, Flask, SQLite, Bootstrap, HTML, CSS, and JavaScript.

---

# Purpose

People may have investments spread across multiple demat accounts and may need to understand lengthy company financial documents such as annual reports and investor presentations.

The application helps users manage their investment portfolio while allowing them to interact with an AI assistant that can understand relevant company financial documents and relate the information to their own portfolio.

The purpose of the Investment Research Assistant is to help users:

* Understand company financial documents.
* Ask questions about information contained in uploaded documents.
* Retrieve information about their own portfolio.
* Understand how a company document relates to their portfolio.
* Understand risks explicitly mentioned in company documents.
* Compare information across multiple company documents.
* Understand their portfolio exposure to companies mentioned in the documents.
* Understand how to use the Investment Portfolio Tracker application.

The assistant provides information and contextual interpretation. It shall not provide financial advice or investment recommendations.

---

# Scope

The application shall:

* Allow users to register and log in securely.
* Allow management of multiple demat accounts.
* Allow recording of buy and sell stock transactions.
* Allow users to manually update stock prices only for currently held stocks.
* Allow users to create and maintain individual AI chats.
* Allow users to view and continue previous chats.
* Allow users to upload relevant company financial documents to individual chats.
* Process uploaded documents using RAG.
* Allow users to ask questions about their portfolio.
* Allow users to ask questions about uploaded financial documents.
* Allow users to ask questions about how to use the application.
* Allow users to ask questions requiring both portfolio and document information.
* Allow the AI assistant to retrieve relevant portfolio information through controlled application functions.
* Allow the AI assistant to retrieve relevant document information through Chroma.
* Allow the AI assistant to choose the needed capability through tool calling rather than keyword-based routing.
* Display current holdings.
* Display demat account-wise portfolio summaries.
* Display overall portfolio summaries.

The application will not integrate with external stock market APIs.

All stock prices will be maintained manually by users and limited to stocks currently held in the portfolio.

The document scope shall focus on company and investment-related financial documents.

---

# Features

1. User Registration
2. User Login
3. User Logout
4. Add Demat Account
5. Edit Demat Account
6. Delete Demat Account
7. Add Buy Transaction
8. Add Sell Transaction
9. Edit Transaction
10. Delete Transaction
11. Update Stock Prices
12. View Holdings
13. View Demat Account Wise Summary
14. View Portfolio Summary
15. Create AI Chat
16. View AI Chat History
17. Continue Existing AI Chat
18. Upload Financial Documents
19. Process Financial Documents using RAG
20. Retrieve Information from Financial Documents
21. AI Investment Research Assistant

---

# Application Architecture

The application shall continue to use a layered architecture.

## Existing Application Components

* `app.py` starts the Flask application.
* `app/routes/` handles HTTP requests, form submission, redirects, and flash messages.
* `app/services/` contains business rules and portfolio calculations.
* `app/repository/` contains SQLite database operations.
* `app/ai/` contains chat orchestration, tool definitions, trusted request context, prompts, and RAG helpers.
* `schema.sql` contains the database schema definition.

The AI functionality shall be added without unnecessarily duplicating existing business logic.

The high-level architecture shall be:

```text
                    Flask Application
                           |
              +------------+-------------+
              |                          |
       Web Application          AI Research Assistant
              |                          |
              |              +-----------+-----------+
              |              |           |           |
              |        Conversation   Portfolio    RAG
              |          Context       Tools       System
              |              |           |           |
              |              |           |         Chroma
              |              |           |
              |              |       Service Layer
              |              |           |
              +--------------+-----------+
                                      |
                                    SQLite
```

The AI assistant shall not directly access SQLite.

The AI assistant shall obtain portfolio information through controlled application functions or services.

Existing portfolio business logic shall be reused where appropriate.

The AI assistant shall use a constrained LangChain tool-calling flow:

1. The user asks a question.
2. The model selects one or more tools.
3. Trusted server-side context supplies authenticated user and active chat information.
4. Tools execute read-only portfolio, application-help, or RAG retrieval logic.
5. Tool results are returned to the model.
6. The model generates the final answer from the returned evidence.

---

# Technical Requirements

## Backend

* Python 3
* Flask

## Security

* Bcrypt Password Hashing
* Session-based authentication

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* Vanilla JavaScript

## Relational Database

* SQLite

SQLite shall store structured application data such as:

* Users
* Demat accounts
* Transactions
* Stock prices
* Chats
* Chat messages
* Document metadata

## Vector Database

* Chroma

Chroma shall store:

* Processed document chunks
* Embeddings
* Retrieval metadata

Chroma shall be used for semantic retrieval of financial-document information.

## AI

* OpenAI API
* LangChain
* LangChain Core
* LangChain OpenAI integration
* LangChain Chroma integration

## Template Engine

* Jinja2

---

# Security Requirements

* Users must register and log in.
* Passwords must be securely hashed using Bcrypt.
* Users must only access their own portfolio data.
* Users must only access their own chats.
* Users must only access documents associated with their own chats.
* Protected pages must require authentication.
* Session-based authentication shall be used.
* Unauthorized users shall be redirected to the login page.
* The AI assistant must operate within the authenticated user's context.
* AI tools must not allow the AI model to choose or modify the authenticated user's identity.
* AI tools shall not provide unrestricted database access.
* AI tools shall be restricted to approved operations.
* AI tools shall read authenticated user and active chat context from trusted server-side state.
* Document retrieval shall be restricted by user and chat ownership.
* Chroma metadata shall contain sufficient information to prevent cross-user and cross-chat retrieval.
* AI tools shall not perform destructive database operations.

---

# Accessibility Requirements

The application must follow WCAG accessibility principles.

Requirements:

* All form controls must have associated labels.
* All pages must be fully keyboard accessible.
* Use semantic HTML elements.
* Provide meaningful page titles and headings.
* Ensure sufficient color contrast.
* Do not rely solely on color.
* Tables must use proper table headers.
* Buttons and links must have meaningful text.
* Forms must provide accessible validation messages.
* Chat controls must be keyboard accessible.
* Document upload controls must be keyboard accessible.
* Chat messages must be accessible to screen readers.

---

# Current Implementation Status

The current codebase has implemented the following:

* user registration, login, and session-based authentication
* demat account CRUD
* transaction CRUD with portfolio calculations
* manual stock-price maintenance for currently held stocks
* persistent chats and chat messages
* document upload, validation, and deletion
* PDF page-level extraction and metadata-preserving chunking
* RAG storage in Chroma with user/chat ownership metadata
* application help content for usage questions
* a tool-calling assistant architecture with trusted user/chat context
* source citations for retrieved document evidence

The remaining work before final sign-off is validation and regression testing in the live browser workflow.
* The application should be usable with NVDA.

---

# UI Requirements

* Each feature must be accessible through clearly labeled buttons or navigation links.
* Forms must provide appropriate input fields.
* All user inputs must be validated.
* Validation errors must be displayed clearly.
* Tables should be used to display holdings, transactions, and summaries.
* The interface should be responsive.
* Bootstrap components should be used for consistency.
* Users shall be able to create a new chat.
* Users shall be able to select an existing chat.
* Users shall be able to view previous messages within a chat.
* Users shall be able to continue an existing chat.
* Users shall be able to upload documents to the selected chat.
* Users shall be able to delete uploaded documents.
* Users shall be able to delete chats.
* The interface shall clearly associate documents with their chat.
* The interface shall clearly distinguish user messages and AI responses.

---

# Functional Requirements

## User Management

Users shall be able to:

* Register
* Login
* Logout

---

## Demat Account Management

Users shall be able to:

* Create demat accounts
* Edit demat accounts
* Delete demat accounts
* View all their demat accounts

Examples:

* Zerodha
* Groww
* Angel One
* ICICI Direct

---

## Transaction Management

Users shall be able to:

* Add buy transactions
* Add sell transactions
* Edit transactions
* Delete transactions

Each transaction shall contain:

* Stock Symbol
* Transaction Type
* Quantity
* Price Per Share
* Transaction Date
* Demat Account

Transaction Types:

* BUY
* SELL

---

## Stock Price Management

Users shall be able to:

* View currently held stocks in a dropdown.
* Update stock prices for those currently held stocks.
* View the saved price for each held stock.

Prices shall be entered manually.

Only stocks currently held across the user's demat accounts shall be available for price updates.

---

# AI Investment Research Assistant

The existing AI Chat Assistant shall be replaced by an AI Investment Research Assistant.

The assistant shall use OpenAI for text generation and LangChain for AI orchestration.

The assistant may use four sources of context:

1. Conversation history.
2. Application and feature information.
3. Relevant portfolio information.
4. Relevant uploaded financial-document information retrieved through RAG.

The assistant shall use only the context relevant to the current question.

The assistant shall not unnecessarily include unrelated information in the prompt.

---

# Chat Management

Users shall be able to:

* Create a new chat.
* View their existing chats.
* Open an existing chat.
* Continue an existing chat.
* View previous messages in a chat.
* Upload documents to a chat.
* Delete individual documents.
* Delete an entire chat.

Each chat shall have its own conversation history.

Each chat may contain multiple financial documents.

Documents uploaded to one chat shall not automatically become available in another chat.

---

# Conversation Memory

The system shall maintain conversation history separately for each chat.

The initial implementation shall use **buffer-style conversation history**.

The assistant shall use relevant previous messages when understanding follow-up questions.

Example:

User:

> What risks does the TCS report mention?

AI:

> The report identifies several risks...

User:

> Explain the second one.

The assistant shall use the previous conversation to understand what "the second one" refers to.

Conversation history shall be associated with the current authenticated user and chat.

Conversation history may be summarized or converted into semantic/vector memory in a future version if chat length creates context or performance limitations.

---

# Application Knowledge

The assistant shall be able to answer questions about how to use the Investment Portfolio Tracker.

Application knowledge may include:

* General application description.
* Feature descriptions.
* Option descriptions.
* Instructions for using features.
* Relevant validation rules.
* Explanations of application behavior.

Application-level and feature-level information shall be provided to the AI only when relevant to the user's question.

Examples:

> How do I add a demat account?

> What does Update Stock Prices do?

> Why can I only update prices for stocks I currently hold?

The assistant may use application and feature summaries to answer such questions.

The application knowledge shall be maintained separately from user financial-document data.

---

# Portfolio Information Retrieval

The AI assistant shall be able to retrieve relevant portfolio information through controlled, read-only application functions.

Potential information includes:

* Current holdings.
* Number of shares held.
* Holdings across demat accounts.
* Current stock value.
* Portfolio weight of a stock.
* Overall portfolio summary.
* Demat-account-wise summary.
* Relevant transaction information.

The AI assistant shall not directly execute arbitrary SQL.

The AI assistant shall not provide a user ID as a parameter to select whose data it accesses.

The authenticated application context shall determine the current user.

Existing service-layer portfolio calculations shall be reused where appropriate.

---

# AI Tools

Selected read-only portfolio and information-retrieval functions shall be exposed to the AI as controlled tools.

Examples include:

* Retrieve stock holdings.
* Retrieve portfolio summary.
* Retrieve account-wise holdings.
* Retrieve relevant transaction information.
* Retrieve portfolio weight.

AI tools shall:

* Have clearly defined purposes.
* Accept only required parameters.
* Operate within the authenticated user's context.
* Return only information required for the operation.
* Not execute arbitrary SQL.
* Not modify portfolio data.
* Not delete data.
* Not bypass application authorization.

The AI shall determine when an available tool is relevant to the user's question.

The application shall not require manually writing an `if/elif` condition for every possible natural-language question.

---

# Financial Document Management

Users shall be able to upload relevant financial documents to an individual chat.

Examples include:

* Company annual reports.
* Investor presentations.
* Company financial reports.
* Other relevant company financial documents.

Uploaded documents shall be treated as temporary inputs for the RAG ingestion process.

The original uploaded document shall not be part of permanent application storage.

During processing, the temporary document shall be:

1. Extracted.
2. Checked for relevance.
3. Chunked.
4. Converted into embeddings.
5. Stored in Chroma with required metadata.

Only after successful ingestion shall the original temporary document be deleted.

If processing or ingestion fails, the system shall not delete the document before the failure has been handled.

The system shall retain the processed information required for future retrieval.

---

# Document Relevance Validation

The system shall check whether an uploaded document is relevant to the application's intended financial-document scope before adding it to Chroma.

The relevance check shall identify whether the document is related to areas such as:

* Company financial information.
* Corporate reporting.
* Company business information.
* Investor information.
* Company risks.
* Financial performance.
* Other relevant investment research information.

The system shall not rely solely on simple keyword matching for document classification.

An AI-based document relevance classification step may be used.

The classification shall determine whether the document is relevant before performing the complete RAG ingestion process.

Example:

### Relevant

A TCS annual report.

Result:

```text
RELEVANT
```

The document may proceed to RAG ingestion.

### Not Relevant

A Python programming tutorial.

Result:

```text
NOT RELEVANT
```

The document shall not be added to Chroma.

The temporary uploaded file shall be deleted after rejection.

---

# Retrieval-Augmented Generation

The system shall use Retrieval-Augmented Generation to answer questions requiring information from uploaded financial documents.

The document processing pipeline shall be:

```text
Uploaded Document
       ↓
Text Extraction
       ↓
Document Relevance Check
       ↓
Text Chunking
       ↓
Embeddings
       ↓
Chroma Vector Database
```

When a user asks a document-related question:

```text
User Question
       ↓
Question Embedding
       ↓
Chroma Similarity Search
       ↓
Relevant Document Chunks
       ↓
Prompt Template
       ↓
OpenAI
       ↓
Response
```

Only documents belonging to the current authenticated user's chat shall be considered.

Chroma metadata shall allow retrieval to be filtered by:

* User
* Chat
* Document

The assistant shall use retrieved document chunks as context when answering document-related questions.

---

# Vector Database Design

Chroma shall store processed information required for document retrieval.

Each document shall be divided into chunks before embeddings are generated.

Chroma shall store:

* Document chunks.
* Embeddings.
* Metadata required for retrieval and authorization.

Metadata shall include, where appropriate:

* User ID.
* Chat ID.
* Document ID.
* Original filename.
* Document type.
* Company information if identified.
* Chunk information.

The original uploaded document shall not be stored permanently.

Chroma shall not replace SQLite as the relational database for application data.

---

# Document Deletion

When a user deletes a document from a chat:

1. The document's associated vectors/chunks shall be deleted from Chroma.
2. The document's metadata shall be deleted from SQLite.

No orphaned vectors belonging to the deleted document should remain available for retrieval.

---

# Chat Deletion

When a user deletes a chat:

1. All messages belonging to the chat shall be deleted from SQLite.
2. All document metadata belonging to the chat shall be deleted from SQLite.
3. All Chroma chunks and embeddings belonging to the chat shall be deleted.
4. The chat record shall be deleted from SQLite.

After deletion, the assistant shall not be able to retrieve information from the deleted chat or its documents.

Chat deletion shall therefore remove the chat's information from both the relational database and vector database.

---

# Context Assembly and Prompt Templates

The system shall use Prompt Templates to construct the input provided to OpenAI.

Depending on the user's question, the prompt may contain:

1. System instructions.
2. Relevant conversation history.
3. Relevant application or feature information.
4. Relevant portfolio information retrieved through AI tools.
5. Relevant document chunks retrieved through RAG.
6. The current user question.

The system shall not automatically include every available source in every request.

Only relevant context shall be included.

---

# Example Context Selection

## Application Question

User:

> How do I add a demat account?

Possible context:

```text
System instructions
+
Relevant conversation history
+
Demat Account feature information
+
Current question
```

Portfolio and document retrieval are not required.

---

## Portfolio Question

User:

> How many TCS shares do I own?

Possible context:

```text
System instructions
+
Relevant conversation history
+
TCS portfolio information
+
Current question
```

Document retrieval is not required.

---

## Document Question

User:

> What risks does the TCS annual report mention?

Possible context:

```text
System instructions
+
Relevant conversation history
+
Relevant TCS report chunks
+
Current question
```

Portfolio retrieval is not required.

---

## Combined Question

User:

> The TCS report mentions currency risk. How significant is TCS in my portfolio?

Possible context:

```text
System instructions
+
Relevant conversation history
+
Relevant TCS report chunks
+
TCS portfolio information
+
Current question
```

---

## Multi-Document Question

User:

> These three reports belong to companies in my portfolio. What risks are common across them?

Possible context:

```text
System instructions
+
Relevant conversation history
+
Relevant chunks from the applicable documents
+
Relevant portfolio information
+
Current question
```

---

# AI Question Types

The assistant shall support the following categories.

## Application Questions

Questions about how the application works or how to use its features.

Example:

> How do I add a demat account?

## Portfolio Questions

Questions about the user's own investment data.

Example:

> How many TCS shares do I hold across my demat accounts?

## Document Questions

Questions about information contained in uploaded financial documents.

Example:

> What is the company's message to investors?

## Combined Portfolio and Document Questions

Questions requiring both document information and portfolio information.

Example:

> What risks does the TCS annual report mention, and what percentage of my portfolio is invested in TCS?

## Multi-Document Questions

Questions involving information from multiple uploaded financial documents.

Example:

> What risks are common across these three reports?

## Follow-Up Questions

Questions that depend on previous messages in the current chat.

Example:

> Explain the second risk.

The assistant shall use conversation history to understand the reference.

---

# Question Scope and Grounding

The assistant shall answer questions using the available and relevant sources:

1. Application knowledge.
2. User portfolio data.
3. Uploaded financial-document information.
4. Relevant conversation history.

The assistant shall not answer unrelated questions merely because the user has uploaded a document.

For example, uploading a Python programming document shall not cause the assistant to become a Python programming tutor.

If the requested information is not available in the relevant application context, portfolio data, conversation history, or uploaded financial documents, the assistant shall state that the required information is unavailable rather than inventing an answer.

The assistant shall not use unrelated uploaded documents as a source for answering an investment-related question.

---

# Risk Interpretation

The assistant may identify and explain risks explicitly mentioned in uploaded financial documents.

The assistant may relate reported risks to the user's portfolio exposure to relevant companies.

For example:

1. A company report identifies currency risk.
2. The user's portfolio contains that company's stock.
3. The system retrieves the user's exposure to that company.
4. The assistant explains that the reported risk is relevant to the user's exposure to that company.

The assistant shall distinguish between:

* Risks explicitly identified in source documents.
* Numerical information explicitly provided by source documents.
* Calculations performed from structured portfolio data.
* Interpretations based on available information.

The assistant shall not invent:

* Risk percentages.
* Risk weights.
* Risk probabilities.
* Portfolio risk scores.
* Financial impacts not supported by available information.

If a company explicitly provides a numerical estimate or scenario in its report, the assistant may report and explain that information.

If a report identifies a risk without providing a numerical weighting, the assistant shall state that no numerical weighting is provided.

The assistant shall not convert the existence of a risk into an invented percentage of portfolio risk.

---

# Financial Advice Restriction

The assistant shall not provide financial advice or investment recommendations.

The assistant shall not tell users:

* Which stock to buy.
* Which stock to sell.
* Whether to hold or sell a particular stock.
* Whether to invest in a particular company.
* Whether a portfolio is good or bad.
* What investment decision the user should make.

The assistant may provide:

* Factual information.
* Document-grounded explanations.
* Portfolio calculations.
* Comparisons supported by available information.
* Explanations of risks explicitly mentioned in source documents.
* Contextual interpretation.

The assistant shall clearly distinguish information and interpretation from financial advice.

---

# Holdings Management

The system shall calculate holdings based on transaction history.

Example:

```text
BUY 10 TCS

BUY 5 TCS

SELL 3 TCS

Current Holding = 12 Shares
```

The existing holdings calculation shall remain the authoritative source for portfolio holdings.

The same business logic shall be used by both the web application and AI portfolio tools where applicable.

---

# Portfolio Summary

The dashboard shall display:

* Total Investment Value
* Current Portfolio Value
* Profit or Loss
* Total Stocks Held
* Total Demat Accounts

### Portfolio Calculation Rule

For this project, total investment is calculated as:

* Total Investment = total BUY amount - total SELL amount

Current portfolio value is the market value of the remaining holdings, based on manually entered stock prices for currently held stocks.

Profit or Loss is calculated as:

* Profit or Loss = Current Portfolio Value - Total Investment

The existing portfolio calculation logic shall be reused when providing portfolio information to the AI assistant.

---

# Demat Account Wise Summary

The system shall display:

* Broker Name
* Number of Stocks
* Investment Value
* Current Value
* Profit or Loss

for each demat account.

---

# Business Rules

1. Users can only view their own data.
2. A demat account belongs to exactly one user.
3. A user can have multiple demat accounts.
4. A transaction belongs to exactly one demat account.
5. A demat account can have multiple transactions.
6. Transaction type must be BUY or SELL.
7. Quantity must be greater than zero.
8. Price per share must be greater than zero.
9. Users must be authenticated before accessing portfolio data.
10. Portfolio value is calculated using holdings and current stock prices.
11. Total investment is calculated as total BUY amount minus total SELL amount.
12. Foreign key relationships must be enforced to maintain data integrity.
13. A chat belongs to exactly one user.
14. A chat can contain multiple messages.
15. A chat can contain multiple documents.
16. A document belongs to exactly one user and one chat.
17. Users can only retrieve documents belonging to their own chats.
18. Document retrieval must respect user and chat ownership.
19. AI portfolio tools must operate within the authenticated user's context.
20. AI tools shall not perform destructive portfolio operations.
21. Document ingestion shall perform a relevance check before adding a document to Chroma.
22. Documents classified as irrelevant shall not be added to Chroma.
23. Original uploaded files shall be deleted after successful RAG ingestion.
24. Failed document processing shall not result in premature deletion of the temporary file.
25. Deleting a document shall remove its metadata from SQLite and its vectors/chunks from Chroma.
26. Deleting a chat shall remove its messages and metadata from SQLite and all associated vectors/chunks from Chroma.
27. The assistant shall use relevant context rather than automatically including all available context.
28. RAG responses shall use retrieved document context when the question requires information from uploaded documents.
29. The assistant shall not invent unavailable numerical risk information.
30. The assistant shall not provide financial advice or investment recommendations.
31. Unrelated documents shall not automatically expand the scope of the assistant.
32. The assistant shall state when required information is unavailable from the permitted sources.

---

# Database Design

## Users

* `user_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `username TEXT NOT NULL`
* `email TEXT NOT NULL UNIQUE`
* `password_hash TEXT NOT NULL`

---

## Demat Accounts

* `account_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `user_id INTEGER NOT NULL`
* `broker_name TEXT NOT NULL`

Foreign Key:

* `user_id REFERENCES users(user_id)`

---

## Transactions

* `transaction_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `account_id INTEGER NOT NULL`
* `stock_symbol TEXT NOT NULL`
* `transaction_type TEXT NOT NULL`
* `quantity INTEGER NOT NULL`
* `price_per_share REAL NOT NULL`
* `transaction_date DATE NOT NULL`

Foreign Key:

* `account_id REFERENCES demat_accounts(account_id)`

---

## Stock Prices

* `price_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `user_id INTEGER NOT NULL`
* `stock_symbol TEXT NOT NULL`
* `current_price REAL NOT NULL`
* `last_updated DATETIME`

Foreign Key:

* `user_id REFERENCES users(user_id)`

---

## Chats

* `chat_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `user_id INTEGER NOT NULL`
* `title TEXT`
* `created_at DATETIME`
* `updated_at DATETIME`

Foreign Key:

* `user_id REFERENCES users(user_id)`

---

## Chat Messages

* `message_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `chat_id INTEGER NOT NULL`
* `role TEXT NOT NULL`
* `content TEXT NOT NULL`
* `created_at DATETIME`

Foreign Key:

* `chat_id REFERENCES chats(chat_id)`

Role values:

* `USER`
* `ASSISTANT`

---

## Documents

* `document_id INTEGER PRIMARY KEY AUTOINCREMENT`
* `chat_id INTEGER NOT NULL`
* `user_id INTEGER NOT NULL`
* `original_filename TEXT NOT NULL`
* `uploaded_at DATETIME`
* `processing_status TEXT NOT NULL`

Foreign Keys:

* `chat_id REFERENCES chats(chat_id)`
* `user_id REFERENCES users(user_id)`

The original document shall only be stored temporarily during processing.

No permanent file path is required because the original document is deleted after successful ingestion.

---

# Chroma Metadata

Each processed document chunk stored in Chroma shall contain metadata sufficient to identify and authorize the source.

Metadata shall include, where appropriate:

* `user_id`
* `chat_id`
* `document_id`
* `original_filename`
* `document_type`
* `company`
* `chunk information`

The metadata shall allow retrieval to be restricted to the current user's chat and documents.

---

# Validation Rules

## Registration

* Username is required.
* Email is required.
* Email must be unique.
* Password is required.
* Password must be at least 8 characters.

## Demat Account

* Broker name is required.

## Transactions

* Stock symbol is required.
* Quantity must be greater than zero.
* Price per share must be greater than zero.
* Transaction type must be BUY or SELL.

## Stock Prices

* At least one current holding must exist before updating stock prices.
* Stock symbol must be one of the user's currently held stocks.
* Current price must be greater than zero.

## Chat

* A user must be authenticated to create or access chats.
* A chat must belong to the authenticated user.

## Documents

* A user must be authenticated to upload documents.
* A document must be associated with an existing chat belonging to the authenticated user.
* Only supported document formats shall be accepted.
* The document must have a valid filename.
* The document must pass the financial-document relevance check before RAG ingestion.
* Documents that fail relevance validation shall not be stored in Chroma.
* Documents that fail processing shall not be considered successfully ingested.

---

# Pages

1. Home Page
2. Register Page
3. Login Page
4. Dashboard
5. Demat Accounts Page
6. Transactions Page
7. Stock Prices Page
8. Holdings Page
9. Demat Account Wise Summary Page
10. Portfolio Summary Page
11. Chat Page
12. Chat History
13. Document Management within Chat

---

# Suggested Folder Structure

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
├── templates/
│   ├── account_summary.html
│   ├── base.html
│   ├── chat.html
│   ├── dashboard.html
│   ├── demat_accounts.html
│   ├── holdings.html
│   ├── home.html
│   ├── login.html
│   ├── portfolio_summary.html
│   ├── register.html
│   ├── stock_prices.html
│   └── transactions.html
└── data/
    ├── chroma/
    └── uploads/
```

The temporary uploaded document does not need to have a permanent directory.

---

# Success Criteria

The project shall be considered complete when:

* Users can register and log in.
* Users can manage demat accounts.
* Users can record buy and sell transactions.
* Users can update stock prices only for currently held stocks.
* Users can create individual AI chats.
* Users can view and continue previous chats.
* Each chat maintains its own conversation history.
* Users can upload relevant financial documents to a chat.
* Uploaded documents undergo a relevance check.
* Irrelevant documents are rejected.
* Relevant documents are processed using RAG.
* Documents are chunked and converted into embeddings.
* Document chunks and embeddings are stored in Chroma.
* Original uploaded files are deleted after successful ingestion.
* Users can ask questions about their uploaded financial documents.
* The assistant can retrieve relevant document information using RAG.
* The assistant can retrieve relevant portfolio information through controlled AI tools.
* Existing portfolio business logic is reused where appropriate.
* The assistant can answer application-related questions using application knowledge.
* The assistant can answer portfolio-related questions.
* The assistant can answer document-related questions.
* The assistant can answer questions requiring both document and portfolio information.
* The assistant can handle relevant multi-document questions.
* The assistant can understand relevant follow-up questions using conversation history.
* The assistant does not retrieve another user's portfolio or documents.
* Deleting a document removes its associated Chroma data.
* Deleting a chat removes its messages and metadata from SQLite and its associated vectors/chunks from Chroma.
* The assistant does not answer unrelated questions merely because an unrelated document was uploaded.
* The assistant does not invent unavailable numerical risk information.
* The assistant does not provide financial advice or investment recommendations.
* The assistant clearly states when required information is unavailable.
* Users can view holdings.
* Users can view demat account-wise summaries.
* Users can view portfolio summaries.
* All structured application data is stored in SQLite.
* Chroma stores processed document information required for semantic retrieval.
* Foreign key relationships are enforced.
* The application is accessible and usable with NVDA.
