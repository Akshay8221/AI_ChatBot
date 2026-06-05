"""User settings model."""

from models import db


class UserSettings(db.Model):
    """Per-user application settings."""

    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    theme = db.Column(db.String(10), default="dark", nullable=False)  # dark, light
    default_model = db.Column(db.String(50), default="gpt-3.5-turbo", nullable=False)
    send_on_enter = db.Column(db.Boolean, default=True, nullable=False)
    show_timestamps = db.Column(db.Boolean, default=True, nullable=False)
    compact_mode = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "default_model": self.default_model,
            "send_on_enter": self.send_on_enter,
            "show_timestamps": self.show_timestamps,
            "compact_mode": self.compact_mode,
        }

    def __repr__(self) -> str:
        return f"<UserSettings for user {self.user_id}>"
