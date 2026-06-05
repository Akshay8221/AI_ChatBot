"""Document model for uploaded files."""

from datetime import datetime, timezone
from models import db


class Document(db.Model):
    """An uploaded document with extracted text for RAG queries."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # pdf, txt, docx
    file_size = db.Column(db.Integer, default=0)  # bytes
    extracted_text = db.Column(db.Text, nullable=True)
    char_count = db.Column(db.Integer, default=0)
    upload_date = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @property
    def size_display(self) -> str:
        """Human-readable file size."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.size_display,
            "char_count": self.char_count,
            "upload_date": self.upload_date.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Document {self.filename}>"
