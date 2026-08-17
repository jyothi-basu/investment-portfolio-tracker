"""Application-usage knowledge base for the assistant tool layer.

This module stores curated UI guidance for the Investment Portfolio Tracker so
the assistant can answer "how do I use the app?" questions with concrete page
names, form steps, and workflow instructions instead of generic summaries.
"""

from collections import OrderedDict
import re


APPLICATION_PURPOSE = (
    "Investment Portfolio Tracker helps users manage stock investments across multiple demat "
    "accounts, maintain manual stock prices, upload financial documents, and ask an AI assistant "
    "about the application, portfolio, or uploaded evidence."
)

NAVIGATION = OrderedDict(
    [
        ("Home", "Landing page with login and register links."),
        ("Register", "Create a new user account."),
        ("Login", "Sign in to the application."),
        ("Dashboard", "View overall investment, portfolio value, profit or loss, and holdings."),
        ("Demat Accounts", "Manage broker accounts for your portfolio."),
        ("Transactions", "Add, edit, and delete BUY or SELL transactions."),
        ("Stock Prices", "Update prices for stocks currently held."),
        ("Holdings", "View your current stock holdings."),
        ("Demat Account Wise Summary", "View account-level portfolio summaries."),
        ("Portfolio Summary", "View the overall portfolio summary."),
        ("Chat", "Ask the AI assistant, upload documents, and review chat history."),
    ]
)

TASKS = OrderedDict(
    [
        (
            "add_demat_account",
            [
                "Open the Demat Accounts page.",
                "Use the add account form on that page.",
                "Enter the broker name.",
                "Submit the form to save the account.",
            ],
        ),
        (
            "add_transaction",
            [
                "Open the Transactions page.",
                "Choose the relevant demat account.",
                "Select BUY or SELL.",
                "Enter the stock symbol, quantity, price per share, and transaction date.",
                "Submit the form to save the transaction.",
            ],
        ),
        (
            "update_stock_prices",
            [
                "Open the Stock Prices page.",
                "Enter the symbol of a stock you currently hold.",
                "Enter the manually maintained current price.",
                "Save the updated price.",
            ],
        ),
        (
            "view_holdings",
            [
                "Open the Holdings page.",
                "Review the current holdings table or list.",
            ],
        ),
        (
            "view_portfolio_summary",
            [
                "Open the Portfolio Summary page.",
                "Review the total investment, current portfolio value, and profit or loss.",
            ],
        ),
        (
            "view_account_summary",
            [
                "Open the Demat Account Wise Summary page.",
                "Review the portfolio summary for each demat account.",
            ],
        ),
        (
            "start_new_chat",
            [
                "Open the Chat page.",
                "Click New Chat.",
                "Use the new chat for a separate topic or document set.",
            ],
        ),
        (
            "switch_chat",
            [
                "Open the Chat page.",
                "Use the Chats sidebar on the left.",
                "Click the chat you want to continue.",
            ],
        ),
        (
            "send_message",
            [
                "Open the Chat page.",
                "Type your question in the Your message box.",
                "Click Send.",
            ],
        ),
        (
            "upload_document",
            [
                "Open the Chat page.",
                "Select the chat that should own the document.",
                "Use the Upload financial document form.",
                "Choose a PDF, DOCX, TXT, or MD file.",
                "Click Upload.",
            ],
        ),
        (
            "ask_document_question",
            [
                "Make sure the document was uploaded into the same chat.",
                "Type a question about the uploaded document in the message box.",
                "Click Send.",
            ],
        ),
        (
            "delete_document",
            [
                "Open the Chat page.",
                "Find the document in the Documents section.",
                "Click Delete for that document.",
            ],
        ),
        (
            "delete_chat",
            [
                "Open the Chat page.",
                "Find the chat in the Chats sidebar.",
                "Click Delete for that chat.",
            ],
        ),
    ]
)

TROUBLESHOOTING = OrderedDict(
    [
        (
            "no_document_sources",
            [
                "Confirm the document was uploaded to the same chat.",
                "Confirm the document still appears in the Documents section.",
                "Ask a question that is actually covered by the uploaded document.",
            ],
        ),
        (
            "no_portfolio_update",
            [
                "Confirm the stock symbol is one you currently hold.",
                "Confirm the transaction values are valid.",
            ],
        ),
        (
            "empty_chat",
            [
                "Confirm you are in the correct chat.",
                "Use New Chat if you want a fresh conversation.",
            ],
        ),
    ]
)

LIMITS = [
    "The assistant is project-specific.",
    "It does not provide financial advice.",
    "It does not use live market data.",
    "It only returns steps and facts from the current application context.",
]


def _score_topic(query, keywords):
    query = (query or "").lower()
    score = 0
    for keyword in keywords:
        if keyword in query:
            score += 1
    return score


def _render_lines(title, lines):
    output = [title]
    output.extend(f"- {line}" for line in lines)
    return output


def _render_task(title, steps):
    output = [title]
    output.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    return output


def _render_navigation():
    output = ["Navigation"]
    output.extend(f"- {page}: {description}" for page, description in NAVIGATION.items())
    return output


def _render_limitations():
    output = ["Assistant limits"]
    output.extend(f"- {item}" for item in LIMITS)
    return output


def _render_full_help():
    sections = [
        _render_lines("Purpose", [APPLICATION_PURPOSE]),
        _render_navigation(),
        _render_task("Add a demat account", TASKS["add_demat_account"]),
        _render_task("Add a transaction", TASKS["add_transaction"]),
        _render_task("Update stock prices", TASKS["update_stock_prices"]),
        _render_task("View holdings", TASKS["view_holdings"]),
        _render_task("View portfolio summary", TASKS["view_portfolio_summary"]),
        _render_task("View demat account summary", TASKS["view_account_summary"]),
        _render_task("Start a new chat", TASKS["start_new_chat"]),
        _render_task("Switch chats", TASKS["switch_chat"]),
        _render_task("Send a message", TASKS["send_message"]),
        _render_task("Upload a document", TASKS["upload_document"]),
        _render_task("Ask about an uploaded document", TASKS["ask_document_question"]),
        _render_task("Delete a document", TASKS["delete_document"]),
        _render_task("Delete a chat", TASKS["delete_chat"]),
        _render_lines("Troubleshooting", sum(TROUBLESHOOTING.values(), [])),
        _render_limitations(),
    ]

    output = []
    for section in sections:
        output.extend(section)
        output.append("")
    return "\n".join(output).rstrip()


def _render_topic_help(topic_title, topic_steps):
    output = [topic_title]
    output.extend(f"{index}. {step}" for index, step in enumerate(topic_steps, start=1))
    output.append("")
    output.extend(_render_limitations())
    return "\n".join(output)


def build_application_help(query=""):
    """Return concise application-help text for the user question."""

    normalized = (query or "").strip().lower()
    if not normalized:
        return _render_full_help()

    task_map = [
        (["demat", "broker", "account"], "Add a demat account", TASKS["add_demat_account"]),
        (["transaction", "buy", "sell"], "Add a transaction", TASKS["add_transaction"]),
        (["stock price", "price"], "Update stock prices", TASKS["update_stock_prices"]),
        (["holdings"], "View holdings", TASKS["view_holdings"]),
        (["portfolio summary", "overall summary", "summary"], "View portfolio summary", TASKS["view_portfolio_summary"]),
        (["account wise", "account summary"], "View demat account summary", TASKS["view_account_summary"]),
        (["new chat", "start chat", "chat"], "Start a new chat", TASKS["start_new_chat"]),
        (["switch chat", "continue chat"], "Switch chats", TASKS["switch_chat"]),
        (["send", "message", "ask"], "Send a message", TASKS["send_message"]),
        (["upload", "document", "pdf", "report"], "Upload a document", TASKS["upload_document"]),
        (["delete document", "remove document"], "Delete a document", TASKS["delete_document"]),
        (["delete chat", "remove chat"], "Delete a chat", TASKS["delete_chat"]),
    ]

    scored = []
    for keywords, title, steps in task_map:
        scored.append((_score_topic(normalized, keywords), title, steps))
    scored.sort(key=lambda item: item[0], reverse=True)

    if scored and scored[0][0] > 0:
        top_score, topic_title, topic_steps = scored[0]
        return _render_topic_help(topic_title, topic_steps)

    if "troubleshoot" in normalized or "problem" in normalized or "error" in normalized:
        troubleshooting_lines = []
        for lines in TROUBLESHOOTING.values():
            troubleshooting_lines.extend(lines)
        output = _render_lines("Troubleshooting", troubleshooting_lines)
        output.append("")
        output.extend(_render_limitations())
        return "\n".join(output)

    return _render_full_help()
