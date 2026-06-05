"""Authentication service."""

import logging
from datetime import datetime, timezone

from models import db
from models.user import User
from models.settings import UserSettings

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication and account management."""

    @staticmethod
    def register_user(username: str, email: str, password: str) -> tuple[User | None, str]:
        """Register a new user.

        Returns:
            Tuple of (User or None, error_message).
        """
        # Validate inputs
        username = username.strip()
        email = email.strip().lower()

        if len(username) < 3:
            return None, "Username must be at least 3 characters."
        if len(username) > 80:
            return None, "Username must be at most 80 characters."
        if len(password) < 8:
            return None, "Password must be at least 8 characters."

        # Check uniqueness
        if User.query.filter_by(username=username).first():
            return None, "Username already taken."
        if User.query.filter_by(email=email).first():
            return None, "Email already registered."

        # Determine role: first user becomes admin
        is_first_user = User.query.count() == 0

        user = User(
            username=username,
            email=email,
            role="admin" if is_first_user else "user",
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()  # Get user.id

        # Create default settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)

        db.session.commit()
        logger.info("User registered: %s (role=%s)", username, user.role)
        return user, ""

    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple[User | None, str]:
        """Authenticate a user by email and password.

        Returns:
            Tuple of (User or None, error_message).
        """
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            return None, "Invalid email or password."

        if not user.is_active:
            return None, "This account has been deactivated."

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        logger.info("User authenticated: %s", user.username)
        return user, ""

    @staticmethod
    def update_profile(user_id: int, username: str | None = None, email: str | None = None) -> tuple[bool, str]:
        """Update user profile fields."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found."

        if username:
            username = username.strip()
            if len(username) < 3:
                return False, "Username must be at least 3 characters."
            existing = User.query.filter(User.username == username, User.id != user_id).first()
            if existing:
                return False, "Username already taken."
            user.username = username

        if email:
            email = email.strip().lower()
            existing = User.query.filter(User.email == email, User.id != user_id).first()
            if existing:
                return False, "Email already in use."
            user.email = email

        db.session.commit()
        logger.info("Profile updated for user %d", user_id)
        return True, ""

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """Change a user's password."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found."

        if not user.check_password(old_password):
            return False, "Current password is incorrect."

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters."

        user.set_password(new_password)
        db.session.commit()
        logger.info("Password changed for user %d", user_id)
        return True, ""

    @staticmethod
    def delete_account(user_id: int, password: str) -> tuple[bool, str]:
        """Delete a user account after password confirmation."""
        user = User.query.get(user_id)
        if not user:
            return False, "User not found."

        if not user.check_password(password):
            return False, "Password is incorrect."

        db.session.delete(user)
        db.session.commit()
        logger.info("Account deleted: user %d", user_id)
        return True, ""
