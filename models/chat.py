"""Chat / Conversation model."""

from datetime import datetime, timezone
from models import db


class Chat(db.Model):
    """A conversation between a user and the AI assistant."""

    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), default="New Chat", nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    messages = db.relationship(
        "Message", backref="chat", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Message.timestamp"
    )

    @property
    def message_count(self) -> int:
        return self.messages.count()

    @property
    def last_message(self):
        return self.messages.order_by(db.desc(db.text("timestamp"))).first()

    @property
    def preview(self) -> str:
        """Return a short preview of the latest message."""
        msg = self.last_message
        if msg:
            return msg.content[:100] + ("..." if len(msg.content) > 100 else "")
        return "No messages yet"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "message_count": self.message_count,
            "preview": self.preview,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Chat {self.id}: {self.title}>"
