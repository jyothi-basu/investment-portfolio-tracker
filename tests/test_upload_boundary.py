"""FastAPI upload boundary tests with the ingestion pipeline mocked."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from app.services import document_service


class TestUploadBoundary:
    def test_upload_streams_from_upload_file_and_completes(self):
        uploaded = Mock(filename="Aster_Technologies_Financial_Report.pdf")
        uploaded.file = BytesIO(b"financial report bytes")

        with patch.object(document_service, "UPLOAD_DIR", Path("test-upload-dir")), \
                    patch.object(document_service, "_ensure_upload_dir"), \
                    patch.object(document_service.Path, "open", mock_open()), \
                    patch.object(document_service.shutil, "copyfileobj") as copy_file, \
                    patch.object(document_service.Path, "unlink"), \
                    patch.object(document_service.db, "fetch_chat", return_value={"chat_id": 5}), \
                    patch.object(document_service.db, "create_document", return_value=41), \
                    patch.object(document_service.db, "update_document_status") as update_status, \
                    patch.object(document_service, "load_document_text", return_value="Aster revenue"), \
                    patch.object(document_service, "classify_document_relevance", return_value={"relevant": True, "document_type": "REPORT", "company": "Aster"}), \
                    patch.object(document_service, "chunk_text", return_value=[{"text": "Aster revenue", "metadata": {}}]), \
                    patch.object(document_service, "add_document_chunks") as add_chunks:
                result = document_service.upload_document(5, 7, uploaded)

        assert result[:2] == (True, "Document uploaded and indexed.")
        copy_file.assert_called_once()
        assert copy_file.call_args.args[0] is uploaded.file
        assert [call.args[2] for call in update_status.call_args_list] == [
            "PROCESSING",
            "COMPLETED",
        ]
        add_chunks.assert_called_once()

    def test_upload_failure_logs_and_returns_existing_failure_contract(self):
        uploaded = Mock(filename="report.txt")
        uploaded.file = BytesIO(b"broken report")

        with patch.object(document_service, "UPLOAD_DIR", Path("test-upload-dir")), \
                    patch.object(document_service, "_ensure_upload_dir"), \
                    patch.object(document_service.Path, "open", mock_open()), \
                    patch.object(document_service.shutil, "copyfileobj"), \
                    patch.object(document_service.Path, "unlink"), \
                    patch.object(document_service.db, "fetch_chat", return_value={"chat_id": 5}), \
                    patch.object(document_service.db, "create_document", return_value=42), \
                    patch.object(document_service.db, "update_document_status") as update_status, \
                    patch.object(document_service, "load_document_text", side_effect=RuntimeError("loader failed")), \
                    patch.object(document_service, "delete_document_chunks"), \
                    patch.object(document_service.logger, "exception") as log_exception:
                result = document_service.upload_document(5, 7, uploaded)

        assert result == (False, "Unable to process the uploaded document.", 42)
        log_exception.assert_called_once()
        assert "FAILED" in [call.args[2] for call in update_status.call_args_list]
