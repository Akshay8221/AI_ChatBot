"""Profile and settings routes."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, logout_user

from models import db
from models.settings import UserSettings
from services.auth_service import AuthService

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update user profile."""
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")

        success, error = AuthService.update_profile(
            current_user.id, username=username, email=email
        )
        if success:
            flash("Profile updated successfully.", "success")
        else:
            flash(error, "danger")

        return redirect(url_for("profile.profile"))

    return render_template("profile.html")


@profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    """Change user password."""
    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("profile.profile"))

    success, error = AuthService.change_password(
        current_user.id, old_password, new_password
    )
    if success:
        flash("Password changed successfully.", "success")
    else:
        flash(error, "danger")

    return redirect(url_for("profile.profile"))


@profile_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    """Delete user account."""
    password = request.form.get("password", "")

    success, error = AuthService.delete_account(current_user.id, password)
    if success:
        logout_user()
        flash("Your account has been deleted.", "info")
        return redirect(url_for("auth.login"))
    else:
        flash(error, "danger")
        return redirect(url_for("profile.profile"))


@profile_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page."""
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    if request.method == "POST":
        user_settings.theme = request.form.get("theme", "dark")
        user_settings.default_model = request.form.get("default_model", "gpt-3.5-turbo")
        user_settings.send_on_enter = request.form.get("send_on_enter") == "on"
        user_settings.show_timestamps = request.form.get("show_timestamps") == "on"
        user_settings.compact_mode = request.form.get("compact_mode") == "on"
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("profile.settings"))

    return render_template("settings.html", settings=user_settings)


@profile_bp.route("/api/settings/theme", methods=["POST"])
@login_required
def toggle_theme():
    """Toggle theme via API."""
    data = request.get_json()
    theme = data.get("theme", "dark")

    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)

    user_settings.theme = theme
    db.session.commit()
    return jsonify({"success": True, "theme": theme})
