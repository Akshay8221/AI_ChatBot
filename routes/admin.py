"""Admin dashboard routes."""

import logging
from functools import wraps
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from models import db
from models.user import User
from models.chat import Chat
from models.message import Message
from models.document import Document

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/admin")
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system statistics."""
    # Gather statistics
    total_users = User.query.count()
    total_chats = Chat.query.count()
    total_messages = Message.query.count()
    total_documents = Document.query.count()

    # Recent activity (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= week_ago).count()
    new_chats_week = Chat.query.filter(Chat.created_at >= week_ago).count()
    new_messages_week = Message.query.filter(Message.timestamp >= week_ago).count()

    # Token usage (approximate)
    total_tokens = db.session.query(db.func.sum(Message.token_count)).scalar() or 0

    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Recent chats
    recent_chats = (
        db.session.query(Chat, User.username)
        .join(User)
        .order_by(Chat.updated_at.desc())
        .limit(10)
        .all()
    )

    # Daily message counts for last 7 days (for chart)
    daily_stats = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Message.query.filter(
            Message.timestamp >= day_start,
            Message.timestamp < day_end,
        ).count()
        daily_stats.append({
            "date": day_start.strftime("%b %d"),
            "count": count,
        })

    stats = {
        "total_users": total_users,
        "total_chats": total_chats,
        "total_messages": total_messages,
        "total_documents": total_documents,
        "total_tokens": total_tokens,
        "new_users_week": new_users_week,
        "new_chats_week": new_chats_week,
        "new_messages_week": new_messages_week,
        "daily_stats": daily_stats,
    }

    return render_template(
        "admin.html",
        stats=stats,
        recent_users=recent_users,
        recent_chats=recent_chats,
    )


@admin_bp.route("/admin/users")
@login_required
@admin_required
def manage_users():
    """User management page."""
    page = request.args.get("page", 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template("admin.html", users=users, view="users")


@admin_bp.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    """Activate or deactivate a user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.dashboard"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    """Change a user's role."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_role = data.get("role", "user")

    if new_role not in ("user", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    if user.id == current_user.id:
        return jsonify({"error": "Cannot change your own role"}), 400

    user.role = new_role
    db.session.commit()
    return jsonify({"success": True, "role": user.role})


@admin_bp.route("/api/admin/stats")
@login_required
@admin_required
def api_stats():
    """API endpoint for dashboard statistics (for AJAX refresh)."""
    stats = {
        "total_users": User.query.count(),
        "total_chats": Chat.query.count(),
        "total_messages": Message.query.count(),
        "total_documents": Document.query.count(),
        "total_tokens": db.session.query(db.func.sum(Message.token_count)).scalar() or 0,
    }
    return jsonify(stats)
