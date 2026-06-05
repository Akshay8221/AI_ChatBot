"""Memory management routes."""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from services.memory_service import MemoryService

memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/memories")
@login_required
def memories_page():
    """List and manage user memories."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    memories = MemoryService.get_memories(
        user_id=current_user.id,
        category=category if category else None,
        query=query if query else None,
    )

    from models.memory import Memory
    return render_template(
        "memories.html",
        memories=memories,
        categories=Memory.CATEGORIES,
        search_query=query,
        active_category=category,
    )


@memory_bp.route("/api/memories/add", methods=["POST"])
@login_required
def add_memory():
    """Add a new memory."""
    data = request.get_json()
    text = data.get("text", "").strip()
    category = data.get("category", "general")

    if not text:
        return jsonify({"error": "Memory text is required"}), 400

    memory = MemoryService.save_memory(current_user.id, text, category)
    return jsonify({"success": True, "memory": memory.to_dict()}), 201


@memory_bp.route("/api/memories/delete/<int:memory_id>", methods=["POST"])
@login_required
def delete_memory(memory_id):
    """Delete a specific memory."""
    success = MemoryService.delete_memory(memory_id, current_user.id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Memory not found"}), 404


@memory_bp.route("/api/memories/clear", methods=["POST"])
@login_required
def clear_memories():
    """Delete all memories."""
    count = MemoryService.delete_all_memories(current_user.id)
    return jsonify({"success": True, "deleted": count})
