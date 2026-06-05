"""Memory model for persistent user context."""

from datetime import datetime, timezone
from models import db


class Memory(db.Model):
    """A saved memory/fact about a user for personalized responses."""

    __tablename__ = "memories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    memory_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="general", nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    CATEGORIES = ["general", "preference", "fact", "instruction"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "memory_text": self.memory_text,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Memory {self.id}: {self.memory_text[:40]}>"
