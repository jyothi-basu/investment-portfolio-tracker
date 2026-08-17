"""Prompt templates and formatting helpers for the assistant orchestration layer."""


PROJECT_ASSISTANT_SYSTEM_PROMPT = (
    "You are a project-specific assistant for the Investment Portfolio Tracker web app. "
    "Answer only questions directly related to this application, its portfolio data, "
    "its uploaded documents, or how to use the app. Use tools when the answer depends "
    "on portfolio information, uploaded-document evidence, or application help. "
    "Do not claim access to live market data. Do not provide financial advice. "
    "Do not invent information. Use supplied evidence as the source of truth. "
    "When answering factual questions about uploaded documents, current tool results are "
    "the authoritative source of evidence. Conversation history may be used to understand "
    "follow-up questions and conversational references, but it must not be treated as "
    "current document evidence. Never attribute a fact to a company or document unless the "
    "current retrieved evidence supports that attribution. If the required current document "
    "evidence is unavailable, say that it cannot be verified from the currently available "
    "uploaded documents instead of guessing from conversation history. Do not invent, "
    "transfer, or mix financial figures between companies. The application will append "
    "document sources when relevant, and you should rely on those retrieved sources. "
    "Keep all existing project scope, financial-advice restrictions, and application-help "
    "behavior unchanged."
)


def format_portfolio_context(summary, holdings):
    """Format an exact portfolio snapshot for tool output."""

    lines = [
        "Portfolio snapshot:",
        f"- Total investment: Rs. {summary['total_investment']:.2f}",
        f"- Current portfolio value: Rs. {summary['current_portfolio_value']:.2f}",
        f"- Profit / loss: Rs. {summary['profit_loss']:.2f}",
        f"- Total stocks held: {summary['total_stocks_held']}",
        f"- Total demat accounts: {summary['total_demat_accounts']}",
    ]

    if holdings:
        lines.append("- Holdings:")
        for item in holdings:
            lines.append(
                f"  - {item['stock_symbol']}: quantity {item['quantity']}, "
                f"current price Rs. {item['current_price']:.2f}, "
                f"current value Rs. {item['current_value']:.2f}"
            )
    else:
        lines.append("- Holdings: none.")

    return "\n".join(lines)


def build_document_citation(metadata):
    """Build a short citation label from document metadata."""

    metadata = metadata or {}
    source_name = metadata.get("original_filename") or "document"
    parts = [source_name]

    page_number = metadata.get("page_number")
    if page_number is not None:
        parts.append(f"page {page_number}")

    chunk_index = metadata.get("chunk_index")
    if chunk_index is not None:
        parts.append(f"chunk {chunk_index}")

    return " | ".join(parts)


def format_document_chunks(chunks):
    """Format retrieved document chunks for tool output."""

    if not chunks:
        return ""

    lines = ["Relevant uploaded document evidence:"]
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata") or {}
        citation = build_document_citation(metadata)
        distance = chunk.get("distance")
        distance_text = f"{distance:.4f}" if isinstance(distance, (int, float)) else "n/a"
        # Preserve the retrieved chunk verbatim so downstream answers can use full tables.
        snippet = (chunk.get("content") or "").strip()

        lines.append(f"{index}. {citation} | distance {distance_text}")
        lines.append(f"   {snippet}")

    return "\n".join(lines)


def format_citations(citations):
    """Format a compact Sources block for the assistant response."""

    citations = [citation.strip() for citation in citations or [] if str(citation).strip()]
    if not citations:
        return ""
    return "\n".join(["Sources:"] + citations)
