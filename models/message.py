"""Message model for chat messages."""

from datetime import datetime, timezone
from models import db


class Message(db.Model):
    """A single message within a conversation."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    token_count = db.Column(db.Integer, default=0)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "role": self.role,
            "content": self.content,
            "token_count": self.token_count,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_openai_format(self) -> dict:
        """Convert to OpenAI message format."""
        return {"role": self.role, "content": self.content}

    def __repr__(self) -> str:
        return f"<Message {self.id} ({self.role})>"
