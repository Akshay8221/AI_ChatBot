"""Chat routes — main chat interface and API endpoints."""

import json
import logging
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, jsonify, Response,
    stream_with_context, current_app,
)
from flask_login import login_required, current_user

from models import db
from models.chat import Chat
from models.message import Message
from models.document import Document
from services.ai_service import AIService
from services.memory_service import MemoryService
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@chat_bp.route("/chat")
@login_required
def chat_page():
    """Main chat interface."""
    chats = (
        Chat.query.filter_by(user_id=current_user.id, is_archived=False)
        .order_by(Chat.is_pinned.desc(), Chat.updated_at.desc())
        .all()
    )
    return render_template("chat.html", chats=chats, active_chat=None)


@chat_bp.route("/chat/<int:chat_id>")
@login_required
def chat_view(chat_id):
    """View a specific conversation."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    chats = (
        Chat.query.filter_by(user_id=current_user.id, is_archived=False)
        .order_by(Chat.is_pinned.desc(), Chat.updated_at.desc())
        .all()
    )
    messages = chat.messages.order_by(Message.timestamp.asc()).all()
    return render_template("chat.html", chats=chats, active_chat=chat, messages=messages)


# ── API Endpoints ──────────────────────────────────────────────────────

@chat_bp.route("/api/chat/new", methods=["POST"])
@login_required
def new_chat():
    """Create a new conversation."""
    chat = Chat(user_id=current_user.id, title="New Chat")
    db.session.add(chat)
    db.session.commit()
    return jsonify({"id": chat.id, "title": chat.title}), 201


@chat_bp.route("/api/chat/send", methods=["POST"])
@login_required
def send_message():
    """Send a message and get a non-streaming AI response."""
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    chat_id = data.get("chat_id")
    user_message = data["message"].strip()
    use_documents = data.get("use_documents", False)

    # Get or create chat
    if chat_id:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
    else:
        chat = Chat(user_id=current_user.id, title="New Chat")
        db.session.add(chat)
        db.session.flush()

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=user_message)
    user_msg.token_count = AIService.estimate_tokens(user_message)
    db.session.add(user_msg)

    # Auto-title on first message
    if chat.message_count == 0:
        chat.title = user_message[:80] + ("..." if len(user_message) > 80 else "")

    # Build context
    memory_context = MemoryService.build_memory_context(current_user.id)

    document_context = ""
    if use_documents:
        docs = Document.query.filter_by(user_id=current_user.id).all()
        if docs:
            doc_texts = [(d.filename, d.extracted_text) for d in docs if d.extracted_text]
            document_context = DocumentService.build_rag_context(user_message, doc_texts)

    # Build message history
    history = [m.to_openai_format() for m in chat.messages.order_by(Message.timestamp.asc()).all()]

    # Generate response
    result = AIService.generate_response(
        messages=history,
        memory_context=memory_context,
        document_context=document_context,
    )

    # Save AI response
    ai_msg = Message(chat_id=chat.id, role="assistant", content=result["content"])
    ai_msg.token_count = result.get("tokens_used", 0)
    db.session.add(ai_msg)

    chat.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "chat_id": chat.id,
        "chat_title": chat.title,
        "message": ai_msg.to_dict(),
        "tokens_used": result.get("tokens_used", 0),
    })


@chat_bp.route("/api/chat/stream", methods=["POST"])
@login_required
def stream_message():
    """Send a message and stream the AI response via SSE."""
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    chat_id = data.get("chat_id")
    user_message = data["message"].strip()
    use_documents = data.get("use_documents", False)

    # Get or create chat
    if chat_id:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
    else:
        chat = Chat(user_id=current_user.id, title="New Chat")
        db.session.add(chat)
        db.session.flush()

    # Save user message
    user_msg = Message(chat_id=chat.id, role="user", content=user_message)
    user_msg.token_count = AIService.estimate_tokens(user_message)
    db.session.add(user_msg)

    # Auto-title on first message
    if chat.message_count == 0:
        chat.title = user_message[:80] + ("..." if len(user_message) > 80 else "")

    db.session.commit()

    # Build context
    memory_context = MemoryService.build_memory_context(current_user.id)

    document_context = ""
    if use_documents:
        docs = Document.query.filter_by(user_id=current_user.id).all()
        if docs:
            doc_texts = [(d.filename, d.extracted_text) for d in docs if d.extracted_text]
            document_context = DocumentService.build_rag_context(user_message, doc_texts)

    # Build message history
    history = [m.to_openai_format() for m in chat.messages.order_by(Message.timestamp.asc()).all()]

    # Send initial metadata
    def generate():
        yield f"data: {json.dumps({'chat_id': chat.id, 'chat_title': chat.title, 'type': 'meta'})}\n\n"

        full_response = []
        for chunk in AIService.stream_response(
            messages=history,
            memory_context=memory_context,
            document_context=document_context,
        ):
            yield chunk
            # Collect tokens for saving
            try:
                chunk_data = json.loads(chunk.replace("data: ", "").strip())
                if "token" in chunk_data:
                    full_response.append(chunk_data["token"])
            except (json.JSONDecodeError, ValueError):
                pass

        # Save AI response to database
        response_text = "".join(full_response)
        if response_text:
            ai_msg = Message(chat_id=chat.id, role="assistant", content=response_text)
            ai_msg.token_count = AIService.estimate_tokens(response_text)
            db.session.add(ai_msg)
            chat.updated_at = datetime.now(timezone.utc)
            db.session.commit()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@chat_bp.route("/api/chat/rename", methods=["POST"])
@login_required
def rename_chat():
    """Rename a conversation."""
    data = request.get_json()
    chat = Chat.query.filter_by(id=data.get("chat_id"), user_id=current_user.id).first()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    chat.title = title[:200]
    db.session.commit()
    return jsonify({"success": True, "title": chat.title})


@chat_bp.route("/api/chat/delete", methods=["POST"])
@login_required
def delete_chat():
    """Delete a conversation."""
    data = request.get_json()
    chat = Chat.query.filter_by(id=data.get("chat_id"), user_id=current_user.id).first()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    db.session.delete(chat)
    db.session.commit()
    return jsonify({"success": True})


@chat_bp.route("/api/chat/pin", methods=["POST"])
@login_required
def pin_chat():
    """Toggle pin on a conversation."""
    data = request.get_json()
    chat = Chat.query.filter_by(id=data.get("chat_id"), user_id=current_user.id).first()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    chat.is_pinned = not chat.is_pinned
    db.session.commit()
    return jsonify({"success": True, "is_pinned": chat.is_pinned})


@chat_bp.route("/api/chat/archive", methods=["POST"])
@login_required
def archive_chat():
    """Toggle archive on a conversation."""
    data = request.get_json()
    chat = Chat.query.filter_by(id=data.get("chat_id"), user_id=current_user.id).first()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    chat.is_archived = not chat.is_archived
    db.session.commit()
    return jsonify({"success": True, "is_archived": chat.is_archived})


@chat_bp.route("/api/chat/search")
@login_required
def search_chats():
    """Search conversations by title or message content."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})

    # Search in chat titles
    title_matches = Chat.query.filter(
        Chat.user_id == current_user.id,
        Chat.title.ilike(f"%{query}%"),
    ).all()

    # Search in messages
    message_chats = (
        db.session.query(Chat)
        .join(Message)
        .filter(Chat.user_id == current_user.id, Message.content.ilike(f"%{query}%"))
        .all()
    )

    # Combine and deduplicate
    seen = set()
    results = []
    for chat in title_matches + message_chats:
        if chat.id not in seen:
            seen.add(chat.id)
            results.append(chat.to_dict())

    return jsonify({"results": results})


@chat_bp.route("/api/chat/export/<int:chat_id>")
@login_required
def export_chat(chat_id):
    """Export a conversation as JSON."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    messages = [m.to_dict() for m in chat.messages.order_by(Message.timestamp.asc()).all()]

    export_data = {
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
        "messages": messages,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    return Response(
        json.dumps(export_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="chat_{chat_id}.json"'},
    )


@chat_bp.route("/api/chat/regenerate", methods=["POST"])
@login_required
def regenerate_response():
    """Regenerate the last AI response in a conversation."""
    data = request.get_json()
    chat_id = data.get("chat_id")
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    # Delete the last assistant message
    last_msg = (
        Message.query.filter_by(chat_id=chat.id, role="assistant")
        .order_by(Message.timestamp.desc())
        .first()
    )
    if last_msg:
        db.session.delete(last_msg)
        db.session.commit()

    # Re-generate using existing history
    history = [m.to_openai_format() for m in chat.messages.order_by(Message.timestamp.asc()).all()]
    memory_context = MemoryService.build_memory_context(current_user.id)

    result = AIService.generate_response(messages=history, memory_context=memory_context)

    ai_msg = Message(chat_id=chat.id, role="assistant", content=result["content"])
    ai_msg.token_count = result.get("tokens_used", 0)
    db.session.add(ai_msg)
    chat.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": ai_msg.to_dict(),
        "tokens_used": result.get("tokens_used", 0),
    })


@chat_bp.route("/api/chat/messages/<int:chat_id>")
@login_required
def get_messages(chat_id):
    """Get all messages for a conversation."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    messages = [m.to_dict() for m in chat.messages.order_by(Message.timestamp.asc()).all()]
    return jsonify({"messages": messages, "title": chat.title})
