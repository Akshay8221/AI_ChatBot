"""Database models package."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User  # noqa: E402, F401
from models.chat import Chat  # noqa: E402, F401
from models.message import Message  # noqa: E402, F401
from models.document import Document  # noqa: E402, F401
from models.memory import Memory  # noqa: E402, F401
from models.settings import UserSettings  # noqa: E402, F401
