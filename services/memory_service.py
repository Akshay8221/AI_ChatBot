"""Memory service for persistent user context."""

import logging
from models import db
from models.memory import Memory

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages user memories for personalized AI responses."""

    @staticmethod
    def save_memory(user_id: int, text: str, category: str = "general") -> Memory:
        """Save a new memory for a user."""
        if category not in Memory.CATEGORIES:
            category = "general"

        memory = Memory(
            user_id=user_id,
            memory_text=text.strip(),
            category=category,
        )
        db.session.add(memory)
        db.session.commit()
        logger.info("Memory saved for user %d: %s...", user_id, text[:50])
        return memory

    @staticmethod
    def get_memories(user_id: int, category: str | None = None, query: str | None = None) -> list[Memory]:
        """Retrieve memories for a user, optionally filtered."""
        q = Memory.query.filter_by(user_id=user_id)

        if category:
            q = q.filter_by(category=category)

        if query:
            q = q.filter(Memory.memory_text.ilike(f"%{query}%"))

        return q.order_by(Memory.created_at.desc()).all()

    @staticmethod
    def delete_memory(memory_id: int, user_id: int) -> bool:
        """Delete a specific memory belonging to a user."""
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if memory:
            db.session.delete(memory)
            db.session.commit()
            logger.info("Memory %d deleted for user %d", memory_id, user_id)
            return True
        return False

    @staticmethod
    def delete_all_memories(user_id: int) -> int:
        """Delete all memories for a user. Returns count deleted."""
        count = Memory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        logger.info("Deleted %d memories for user %d", count, user_id)
        return count

    @staticmethod
    def build_memory_context(user_id: int) -> str:
        """Build a formatted context string from user memories for AI prompts."""
        memories = Memory.query.filter_by(user_id=user_id).order_by(
            Memory.created_at.desc()
        ).limit(20).all()

        if not memories:
            return ""

        lines = ["Here are things to remember about this user:"]
        for mem in memories:
            lines.append(f"- [{mem.category}] {mem.memory_text}")

        return "\n".join(lines)

    @staticmethod
    def count_memories(user_id: int) -> int:
        """Count total memories for a user."""
        return Memory.query.filter_by(user_id=user_id).count()
