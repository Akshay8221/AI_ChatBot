"""Document upload and RAG query routes."""

import os
import logging
from uuid import uuid4

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db
from models.document import Document
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/documents")
@login_required
def documents_page():
    """List user's uploaded documents."""
    docs = (
        Document.query.filter_by(user_id=current_user.id)
        .order_by(Document.upload_date.desc())
        .all()
    )
    return render_template("documents.html", documents=docs)


@documents_bp.route("/documents/upload", methods=["POST"])
@login_required
def upload_document():
    """Upload and process a document."""
    if "file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("documents.documents_page"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("documents.documents_page"))

    filename = secure_filename(file.filename)
    ext = DocumentService.get_file_extension(filename)

    if not DocumentService.allowed_file(filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash(f"File type .{ext} is not supported. Allowed: PDF, DOCX, TXT.", "danger")
        return redirect(url_for("documents.documents_page"))

    # Ensure uploads directory exists
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    user_dir = os.path.join(upload_dir, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    # Save file with unique name to avoid conflicts
    unique_name = f"{uuid4().hex}_{filename}"
    filepath = os.path.join(user_dir, unique_name)
    file.save(filepath)

    # Extract text
    extracted_text = DocumentService.process_file(filepath, ext)
    file_size = DocumentService.get_file_size(filepath)

    # Save to database
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        filepath=filepath,
        file_type=ext,
        file_size=file_size,
        extracted_text=extracted_text,
        char_count=len(extracted_text) if extracted_text else 0,
    )
    db.session.add(doc)
    db.session.commit()

    if extracted_text:
        flash(f"'{filename}' uploaded and processed successfully ({doc.size_display}, {doc.char_count:,} characters extracted).", "success")
    else:
        flash(f"'{filename}' uploaded but no text could be extracted.", "warning")

    return redirect(url_for("documents.documents_page"))


@documents_bp.route("/documents/delete/<int:doc_id>", methods=["POST"])
@login_required
def delete_document(doc_id):
    """Delete an uploaded document."""
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()

    # Delete file from disk
    try:
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    except OSError as e:
        logger.warning("Could not delete file %s: %s", doc.filepath, e)

    db.session.delete(doc)
    db.session.commit()
    flash(f"Document '{doc.filename}' deleted.", "info")
    return redirect(url_for("documents.documents_page"))


@documents_bp.route("/api/documents/query", methods=["POST"])
@login_required
def query_documents():
    """RAG query against user's documents."""
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    docs = Document.query.filter_by(user_id=current_user.id).all()
    if not docs:
        return jsonify({"error": "No documents uploaded"}), 400

    doc_texts = [(d.filename, d.extracted_text) for d in docs if d.extracted_text]
    context = DocumentService.build_rag_context(query, doc_texts)

    return jsonify({
        "context": context,
        "documents_searched": len(doc_texts),
    })
