# 🤖 Smart AI Assistant

A production-ready, ChatGPT-style AI chatbot web application built with Python, Flask, and OpenAI-compatible APIs. Features a modern dark/light UI, real-time streaming responses, RAG document chat, memory system, admin dashboard, and full user management.

---

## ✨ Features

### 💬 AI Chat
- **Streaming responses** via Server-Sent Events (SSE)
- **Multiple conversations** with full CRUD management
- **Markdown rendering** with syntax-highlighted code blocks
- **Conversation memory** — context retained across messages
- **Pin, rename, archive, export, search** conversations
- **Regenerate** and **copy** responses
- **Keyboard shortcuts** (Ctrl+N, Ctrl+/, Escape)

### 📄 RAG Document Chat
- Upload **PDF, DOCX, TXT** files
- Automatic **text extraction** and chunking
- **Ask questions** about your documents
- Context injection with **source references**
- Toggle RAG mode per conversation

### 🧠 Memory System
- Save **preferences, facts, and instructions**
- AI automatically uses memories for **personalized responses**
- Full CRUD: add, search, filter, delete

### 👤 Authentication
- User **registration and login**
- **Profile management** — update username, email, password
- **Account deletion** with password confirmation
- First registered user becomes **admin**

### 🛡️ Admin Dashboard
- **System statistics** — users, chats, messages, tokens
- **7-day activity chart** (Chart.js)
- **User management** — activate/deactivate users
- **Recent activity** feed

### 🎨 Modern UI
- **Dark / Light mode** toggle with persistence
- **Responsive design** — works on mobile and desktop
- **Glassmorphism** cards, gradient accents, smooth animations
- **ChatGPT-inspired** layout with sidebar

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+**
- **pip**
- An **OpenAI API key** (or compatible API)

### 1. Clone & Setup

```bash
cd ChatBot

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key
# OPENAI_API_KEY=sk-your-key-here
# SECRET_KEY=your-random-secret-key
```

### 3. Initialize Database

```bash
flask db init
flask db migrate -m "initial migration"
flask db upgrade
```

### 4. Run the Application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

### 5. First Steps
1. **Register** a new account (first user becomes admin)
2. **Start chatting** with the AI
3. **Upload documents** and ask questions about them
4. **Save memories** for personalized responses
5. **Explore settings** for theme and preferences

---

## 🐳 Docker Deployment

### Quick Start with Docker

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Build and run
docker compose up -d

# Application available at http://localhost:8000
```

### Docker Commands

```bash
# View logs
docker compose logs -f web

# Stop
docker compose down

# Rebuild after changes
docker compose up -d --build

# Reset database
docker compose down -v
docker compose up -d
```

---

## 📁 Project Structure

```
ChatBot/
├── app.py                  # Flask application factory
├── config.py               # Configuration classes
├── requirements.txt        # Python dependencies
├── gunicorn.conf.py        # Production server config
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service orchestration
│
├── models/                 # SQLAlchemy database models
│   ├── user.py             # User authentication model
│   ├── chat.py             # Conversation model
│   ├── message.py          # Message model
│   ├── document.py         # Uploaded document model
│   ├── memory.py           # User memory model
│   └── settings.py         # User settings model
│
├── routes/                 # Flask blueprints
│   ├── auth.py             # Login, register, logout
│   ├── chat.py             # Chat interface & API
│   ├── profile.py          # Profile & settings
│   ├── documents.py        # Document upload & RAG
│   ├── admin.py            # Admin dashboard
│   └── memory.py           # Memory management
│
├── services/               # Business logic layer
│   ├── ai_service.py       # OpenAI API integration
│   ├── document_service.py # File processing & RAG
│   ├── memory_service.py   # Memory management
│   └── auth_service.py     # Authentication logic
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout
│   ├── chat.html           # Main chat interface
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── dashboard.html      # User dashboard
│   ├── profile.html        # Profile management
│   ├── documents.html      # Document management
│   ├── memories.html       # Memory management
│   ├── admin.html          # Admin dashboard
│   ├── settings.html       # Settings page
│   └── errors/             # Error pages
│
├── static/
│   ├── css/style.css       # Complete design system
│   └── js/
│       ├── chat.js         # Chat engine
│       ├── theme.js        # Theme manager
│       └── admin.js        # Admin scripts
│
├── uploads/                # User uploaded files
└── instance/               # SQLite database
```

---

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-key...` |
| `DATABASE_URL` | Database connection string | SQLite (local) |
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | AI model to use | `gpt-3.5-turbo` |
| `OPENAI_MAX_TOKENS` | Max response tokens | `2048` |
| `OPENAI_TEMPERATURE` | Response creativity | `0.7` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `30` |

### Using Alternative APIs

You can use any OpenAI-compatible API:

```env
# Ollama (local)
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_MODEL=llama3

# Azure OpenAI
OPENAI_API_BASE=https://your-resource.openai.azure.com/openai/deployments/your-deployment
OPENAI_API_KEY=your-azure-key

# LM Studio
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_MODEL=local-model
```

---

## 🔒 Security

- Password hashing via `werkzeug.security`
- CSRF protection on all forms
- Session-based authentication with Flask-Login
- File upload validation (type, size)
- Input sanitization
- Environment variables for secrets
- Non-root Docker container

---

## 📝 License

MIT License — free for personal and commercial use.
