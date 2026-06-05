/* =============================================
   Smart AI Assistant — Chat Engine
   ============================================= */

// ── State ─────────────────────────────────────
let currentChatId = document.getElementById('current-chat-id')?.value || null;
let isGenerating = false;
let currentEventSource = null;
let abortController = null;

const csrfToken = document.getElementById('csrf-token')?.value || '';
const username = document.getElementById('current-username')?.value || 'User';

// ── DOM Elements ──────────────────────────────
const messageInput = document.getElementById('message-input');
const chatMessages = document.getElementById('chat-messages');
const btnSend = document.getElementById('btn-send');
const btnStop = document.getElementById('btn-stop');
const typingIndicator = document.getElementById('typing-indicator');
const chatTitle = document.getElementById('chat-title');
const welcomeScreen = document.getElementById('welcome-screen');
const sidebar = document.getElementById('sidebar');

// ── Initialization ────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Auto-resize textarea
    if (messageInput) {
        messageInput.addEventListener('input', autoResizeTextarea);
        messageInput.addEventListener('keydown', handleKeyDown);
    }

    // Sidebar toggle
    document.getElementById('sidebar-toggle')?.addEventListener('click', toggleSidebar);
    document.getElementById('sidebar-close')?.addEventListener('click', closeSidebar);

    // New chat button
    document.getElementById('btn-new-chat')?.addEventListener('click', newChat);

    // Search
    document.getElementById('chat-search')?.addEventListener('input', debounce(handleSearch, 300));

    // Render markdown in existing messages
    renderAllMarkdown();

    // Scroll to bottom
    scrollToBottom();

    // Keyboard shortcuts
    document.addEventListener('keydown', handleGlobalShortcuts);
});

// ── Send Message ──────────────────────────────
async function sendMessage() {
    if (isGenerating) return;

    const message = messageInput?.value.trim();
    if (!message) return;

    // Clear input
    messageInput.value = '';
    autoResizeTextarea();

    // Hide welcome screen
    if (welcomeScreen) welcomeScreen.style.display = 'none';

    // Add user message to UI
    appendMessage('user', message);

    // Show typing indicator
    setGenerating(true);

    const useDocuments = document.getElementById('use-documents')?.checked || false;

    try {
        // Use streaming endpoint
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                message: message,
                chat_id: currentChatId || null,
                use_documents: useDocuments,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Process SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiMessageEl = null;
        let fullResponse = '';

        abortController = new AbortController();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                try {
                    const data = JSON.parse(line.slice(6));

                    // Metadata
                    if (data.type === 'meta') {
                        currentChatId = data.chat_id;
                        document.getElementById('current-chat-id').value = data.chat_id;
                        if (chatTitle) chatTitle.textContent = data.chat_title;
                        updateSidebarChat(data.chat_id, data.chat_title);
                        continue;
                    }

                    // Error
                    if (data.error) {
                        if (!aiMessageEl) {
                            aiMessageEl = appendMessage('assistant', '');
                        }
                        updateMessageContent(aiMessageEl, `⚠️ ${data.error}`);
                        break;
                    }

                    // Token
                    if (data.token) {
                        if (!aiMessageEl) {
                            hideTypingIndicator();
                            aiMessageEl = appendMessage('assistant', '');
                        }
                        fullResponse += data.token;
                        updateMessageContent(aiMessageEl, fullResponse);
                        scrollToBottom();
                    }

                    // Done
                    if (data.done) {
                        break;
                    }
                } catch (e) {
                    // Ignore parse errors for incomplete chunks
                }
            }
        }

        // Final render with full markdown
        if (aiMessageEl && fullResponse) {
            renderMarkdown(aiMessageEl.querySelector('.message-body'));
            addMessageActions(aiMessageEl);
        }

    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Send error:', error);
            appendMessage('assistant', '⚠️ Failed to get a response. Please check your connection and API key.');
        }
    } finally {
        setGenerating(false);
    }
}

// ── Stop Generation ───────────────────────────
function stopGeneration() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
    setGenerating(false);
}

// ── Regenerate Response ───────────────────────
async function regenerateResponse() {
    if (!currentChatId || isGenerating) return;

    // Remove last AI message from UI
    const messages = chatMessages.querySelectorAll('.message-assistant');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }

    setGenerating(true);

    try {
        const response = await fetch('/api/chat/regenerate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ chat_id: currentChatId }),
        });

        const data = await response.json();
        if (data.message) {
            const el = appendMessage('assistant', data.message.content);
            renderMarkdown(el.querySelector('.message-body'));
            addMessageActions(el);
        }
    } catch (error) {
        console.error('Regenerate error:', error);
        showToast('Failed to regenerate response.', 'danger');
    } finally {
        setGenerating(false);
    }
}

// ── Message DOM Helpers ───────────────────────
function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message message-${role}`;

    const avatarContent = role === 'user'
        ? `<span>${username[0].toUpperCase()}</span>`
        : '<i class="bi bi-robot"></i>';

    const authorName = role === 'user' ? 'You' : 'Smart AI';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.innerHTML = `
        <div class="message-avatar">${avatarContent}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-body ${role === 'assistant' ? 'markdown-body' : ''}">${escapeHtml(content)}</div>
        </div>
    `;

    // Insert before typing indicator
    if (typingIndicator) {
        chatMessages.insertBefore(div, typingIndicator);
    } else {
        chatMessages.appendChild(div);
    }

    scrollToBottom();
    return div;
}

function updateMessageContent(messageEl, content) {
    const body = messageEl.querySelector('.message-body');
    if (body) {
        // Render markdown incrementally
        body.innerHTML = renderMarkdownString(content);
    }
}

function addMessageActions(messageEl) {
    const existing = messageEl.querySelector('.message-actions');
    if (existing) return;

    const actions = document.createElement('div');
    actions.className = 'message-actions';
    actions.innerHTML = `
        <button class="btn-msg-action" onclick="copyMessage(this)" title="Copy">
            <i class="bi bi-clipboard"></i> Copy
        </button>
        <button class="btn-msg-action" onclick="regenerateResponse()" title="Regenerate">
            <i class="bi bi-arrow-clockwise"></i> Regenerate
        </button>
    `;
    messageEl.querySelector('.message-content').appendChild(actions);
}

// ── Markdown Rendering ────────────────────────
function renderMarkdownString(text) {
    if (typeof marked === 'undefined') return escapeHtml(text);

    marked.setOptions({
        highlight: function(code, lang) {
            if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (e) {}
            }
            return code;
        },
        breaks: true,
        gfm: true,
    });

    let html = marked.parse(text);

    // Add code headers with copy buttons and language labels
    html = html.replace(/<pre><code class="language-(\w+)">/g, (match, lang) => {
        return `<div class="code-header"><span>${lang}</span><button class="code-copy-btn" onclick="copyCodeBlock(this)"><i class="bi bi-clipboard"></i> Copy</button></div><pre><code class="language-${lang}">`;
    });

    // Add copy button to code blocks without language
    html = html.replace(/<pre><code>(?!<)/g, () => {
        return `<div class="code-header"><span>code</span><button class="code-copy-btn" onclick="copyCodeBlock(this)"><i class="bi bi-clipboard"></i> Copy</button></div><pre><code>`;
    });

    return html;
}

function renderMarkdown(el) {
    if (!el) return;
    const raw = el.textContent || el.innerText;
    el.innerHTML = renderMarkdownString(raw);
}

function renderAllMarkdown() {
    document.querySelectorAll('.message-assistant .markdown-body').forEach(el => {
        renderMarkdown(el);
    });
}

// ── Copy Functions ────────────────────────────
function copyMessage(btn) {
    const body = btn.closest('.message-content').querySelector('.message-body');
    const text = body.innerText || body.textContent;
    navigator.clipboard.writeText(text).then(() => {
        const icon = btn.querySelector('i');
        icon.className = 'bi bi-check-lg';
        btn.querySelector('i + text, i ~ *')
        setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);
        showToast('Copied to clipboard!', 'success');
    });
}

function copyCodeBlock(btn) {
    const pre = btn.closest('.code-header')?.nextElementSibling;
    if (!pre) return;
    const code = pre.querySelector('code');
    const text = code.innerText || code.textContent;
    navigator.clipboard.writeText(text).then(() => {
        btn.innerHTML = '<i class="bi bi-check-lg"></i> Copied!';
        setTimeout(() => {
            btn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
        }, 2000);
    });
}

// ── Chat CRUD ─────────────────────────────────
async function newChat() {
    try {
        const response = await fetch('/api/chat/new', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
        });
        const data = await response.json();
        window.location.href = '/chat/' + data.id;
    } catch (error) {
        console.error('New chat error:', error);
        showToast('Failed to create new chat.', 'danger');
    }
}

function loadChat(chatId) {
    window.location.href = '/chat/' + chatId;
}

async function renameChat(chatId, currentTitle) {
    const title = prompt('Rename conversation:', currentTitle);
    if (!title || title === currentTitle) return;

    try {
        const response = await fetch('/api/chat/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ chat_id: chatId, title }),
        });
        const data = await response.json();
        if (data.success) {
            // Update sidebar
            const item = document.querySelector(`[data-chat-id="${chatId}"] .conv-title`);
            if (item) item.textContent = data.title;
            if (currentChatId == chatId && chatTitle) {
                chatTitle.textContent = data.title;
            }
            showToast('Chat renamed.', 'success');
        }
    } catch (error) {
        showToast('Failed to rename.', 'danger');
    }
}

async function deleteChat(chatId) {
    if (!confirm('Delete this conversation?')) return;

    try {
        const response = await fetch('/api/chat/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ chat_id: chatId }),
        });
        const data = await response.json();
        if (data.success) {
            const item = document.querySelector(`[data-chat-id="${chatId}"]`);
            if (item) item.remove();

            if (currentChatId == chatId) {
                window.location.href = '/chat';
            }
            showToast('Chat deleted.', 'info');
        }
    } catch (error) {
        showToast('Failed to delete.', 'danger');
    }
}

async function pinChat(chatId) {
    try {
        const response = await fetch('/api/chat/pin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ chat_id: chatId }),
        });
        const data = await response.json();
        if (data.success) {
            showToast(data.is_pinned ? 'Chat pinned.' : 'Chat unpinned.', 'success');
            location.reload();
        }
    } catch (error) {
        showToast('Failed to pin.', 'danger');
    }
}

function exportChat(chatId) {
    window.open('/api/chat/export/' + chatId, '_blank');
}

// ── Search ────────────────────────────────────
async function handleSearch(e) {
    const query = e.target.value.trim();
    if (!query) {
        // Show all conversations
        document.querySelectorAll('.conv-item').forEach(el => el.style.display = '');
        document.querySelectorAll('.conv-section').forEach(el => el.style.display = '');
        return;
    }

    try {
        const response = await fetch(`/api/chat/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        const matchIds = new Set(data.results.map(r => r.id));

        document.querySelectorAll('.conv-item').forEach(el => {
            const chatId = parseInt(el.dataset.chatId);
            el.style.display = matchIds.has(chatId) ? '' : 'none';
        });
    } catch (error) {
        console.error('Search error:', error);
    }
}

// ── Sidebar ───────────────────────────────────
function toggleSidebar() {
    sidebar.classList.toggle('open');
    toggleOverlay();
}

function closeSidebar() {
    sidebar.classList.remove('open');
    removeOverlay();
}

function toggleOverlay() {
    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', closeSidebar);
        document.body.appendChild(overlay);
    }
    overlay.classList.toggle('active', sidebar.classList.contains('open'));
}

function removeOverlay() {
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) overlay.classList.remove('active');
}

function updateSidebarChat(chatId, title) {
    const existing = document.querySelector(`[data-chat-id="${chatId}"]`);
    if (existing) {
        existing.querySelector('.conv-title').textContent = title;
        return;
    }

    // Add new chat to sidebar
    const section = document.querySelector('.conv-section:last-child') || createSection('Recent');
    const item = document.createElement('div');
    item.className = 'conv-item active';
    item.dataset.chatId = chatId;
    item.onclick = () => loadChat(chatId);
    item.innerHTML = `
        <div class="conv-item-content">
            <i class="bi bi-chat-text"></i>
            <span class="conv-title">${escapeHtml(title)}</span>
        </div>
        <div class="conv-item-actions">
            <button class="btn-icon-sm" onclick="event.stopPropagation(); pinChat(${chatId})" title="Pin">
                <i class="bi bi-pin-angle"></i>
            </button>
            <button class="btn-icon-sm" onclick="event.stopPropagation(); renameChat(${chatId}, '${escapeHtml(title)}')" title="Rename">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn-icon-sm text-danger" onclick="event.stopPropagation(); deleteChat(${chatId})" title="Delete">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;

    // Deactivate other items
    document.querySelectorAll('.conv-item.active').forEach(el => el.classList.remove('active'));

    section.insertBefore(item, section.querySelector('.conv-item'));
}

// ── File Upload ───────────────────────────────
function handleFileUpload(input) {
    if (!input.files.length) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('csrf_token', csrfToken);

    showToast(`Uploading "${file.name}"...`, 'info');

    fetch('/documents/upload', {
        method: 'POST',
        body: formData,
    })
    .then(response => {
        if (response.redirected) {
            showToast('File uploaded successfully!', 'success');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showToast('Upload failed.', 'danger');
    });

    input.value = '';
}

// ── UI Helpers ────────────────────────────────
function setGenerating(state) {
    isGenerating = state;
    if (btnSend) btnSend.style.display = state ? 'none' : '';
    if (btnStop) btnStop.style.display = state ? '' : 'none';
    if (state) showTypingIndicator();
    else hideTypingIndicator();
}

function showTypingIndicator() {
    if (typingIndicator) typingIndicator.style.display = '';
    scrollToBottom();
}

function hideTypingIndicator() {
    if (typingIndicator) typingIndicator.style.display = 'none';
}

function scrollToBottom() {
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function autoResizeTextarea() {
    if (!messageInput) return;
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
}

function useSuggestion(text) {
    if (messageInput) {
        messageInput.value = text;
        autoResizeTextarea();
        sendMessage();
    }
}

// ── Keyboard Handling ─────────────────────────
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function handleGlobalShortcuts(e) {
    // Ctrl+N: New chat
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        newChat();
    }
    // Ctrl+/: Toggle sidebar
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        toggleSidebar();
    }
    // Escape: Stop generation
    if (e.key === 'Escape' && isGenerating) {
        stopGeneration();
    }
}

// ── Utilities ─────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function createSection(label) {
    const list = document.getElementById('conversation-list');
    const section = document.createElement('div');
    section.className = 'conv-section';
    section.innerHTML = `<div class="conv-section-label"><i class="bi bi-clock-history"></i> ${label}</div>`;
    list.appendChild(section);
    return section;
}
