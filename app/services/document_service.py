"""Document upload and ingestion service bridging chat uploads to the RAG pipeline."""

from pathlib import Path

from werkzeug.utils import secure_filename

from app.ai.rag import add_document_chunks, chunk_text, classify_document_relevance, delete_document_chunks, load_document_text
from app.repository import db


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _get_document_path(document_id, original_filename):
    safe_name = secure_filename(original_filename or "")
    if not safe_name:
        safe_name = "document"
    return UPLOAD_DIR / f"{document_id}_{safe_name}"


def _has_allowed_extension(filename):
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def _flatten_pdf_pages(pages):
    return "\n\n".join((page.get("text") or "").strip() for page in pages if (page.get("text") or "").strip())


def list_documents_for_chat(chat_id, user_id):
    return db.fetch_documents_for_chat(chat_id, user_id)


def upload_document(chat_id, user_id, uploaded_file):
    if not db.fetch_chat(chat_id, user_id):
        return False, "Chat not found.", None
    if uploaded_file is None:
        return False, "Please choose a file to upload.", None
    if not uploaded_file.filename or not uploaded_file.filename.strip():
        return False, "The uploaded file must have a valid filename.", None
    if not _has_allowed_extension(uploaded_file.filename):
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"Unsupported file type. Allowed types: {allowed}.", None

    original_filename = secure_filename(uploaded_file.filename.strip())
    if not original_filename:
        return False, "The uploaded file must have a valid filename.", None

    document_id = db.create_document(chat_id, user_id, original_filename, processing_status="UPLOADED")
    file_path = _get_document_path(document_id, original_filename)
    try:
        _ensure_upload_dir()
        uploaded_file.save(file_path)
        db.update_document_status(document_id, user_id, "PROCESSING")

        extracted_text = load_document_text(file_path)
        if isinstance(extracted_text, list):
            # PDF pages remain separate so downstream chunks can keep page-level metadata.
            classification_text = _flatten_pdf_pages(extracted_text)
        else:
            classification_text = extracted_text

        classification = classify_document_relevance(classification_text, original_filename)
        if not classification["relevant"]:
            db.update_document_status(document_id, user_id, "REJECTED")
            try:
                delete_document_chunks(document_id, user_id)
            except Exception as exc:
                print(f"[document-delete-chunks] document_id={document_id} user_id={user_id} failed: {exc!r}")
                pass
            file_path.unlink(missing_ok=True)
            return False, classification["reason"], document_id

        chunks = []
        if isinstance(extracted_text, list):
            global_chunk_index = 0
            for page in extracted_text:
                page_text = (page.get("text") or "").strip()
                page_number = page.get("page_number")
                if not page_text:
                    continue
                # Chunk each page independently to preserve page attribution in vector metadata.
                page_chunks = chunk_text(
                    page_text,
                    source_name=original_filename,
                    page_number=page_number,
                    chunk_index_start=global_chunk_index,
                )
                chunks.extend(page_chunks)
                global_chunk_index += len(page_chunks)
        else:
            chunks = chunk_text(extracted_text, source_name=original_filename)

        if not chunks:
            db.update_document_status(document_id, user_id, "FAILED")
            return False, "No extractable text was found in the uploaded document.", document_id

        add_document_chunks(
            document_id=document_id,
            user_id=user_id,
            chat_id=chat_id,
            original_filename=original_filename,
            chunks=chunks,
            document_type=classification.get("document_type"),
            company=classification.get("company"),
        )
        db.update_document_status(document_id, user_id, "COMPLETED")
        file_path.unlink(missing_ok=True)
    except Exception:
        db.update_document_status(document_id, user_id, "FAILED")
        try:
            delete_document_chunks(document_id, user_id)
        except Exception as exc:
            print(f"[document-delete-chunks] document_id={document_id} user_id={user_id} failed: {exc!r}")
            pass
        return False, "Unable to process the uploaded document.", document_id

    return True, "Document uploaded and indexed.", document_id


def delete_document(document_id, user_id):
    document = db.fetch_document(document_id, user_id)
    if not document:
        return False, "Document not found."

    try:
        delete_document_chunks(document_id, user_id)
    except Exception as exc:
        print(f"[document-delete-chunks] document_id={document_id} user_id={user_id} failed: {exc!r}")
        return False, "Unable to delete the document from the search index."

    file_path = _get_document_path(document["document_id"], document["original_filename"])
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass

    db.delete_document(document_id, user_id)
    return True, "Document deleted."
