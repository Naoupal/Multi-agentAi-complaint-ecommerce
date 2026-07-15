// ============================================
// Multi-Agent Complaint Resolution — App Logic
// ============================================

const API_BASE = window.location.origin;

// --- DOM References ---
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const btnSend = document.getElementById('btnSend');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const traceBody = document.getElementById('traceBody');
const traceCount = document.getElementById('traceCount');
const agentBadges = document.querySelectorAll('.agent-badge');

// --- State ---
let isProcessing = false;
let activeAgents = new Set();

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  lucide.createIcons();

  checkHealth();
  setInterval(checkHealth, 30000); // check every 30s

  btnSend.addEventListener('click', sendComplaint);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendComplaint();
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  // Example cards
  document.querySelectorAll('.example-card').forEach(card => {
    card.addEventListener('click', () => {
      const text = card.dataset.complaint;
      if (text && !isProcessing) {
        chatInput.value = text;
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        chatInput.focus();
      }
    });
  });
});

// --- Health Check ---
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      statusDot.classList.add('online');
      statusText.textContent = 'API Online';
    } else {
      throw new Error('not ok');
    }
  } catch {
    statusDot.classList.remove('online');
    statusText.textContent = 'API Offline';
  }
}

// --- Send Complaint ---
async function sendComplaint() {
  const msg = chatInput.value.trim();
  if (!msg || isProcessing) return;

  isProcessing = true;
  btnSend.disabled = true;
  activeAgents.clear();
  updateAgentBadges();

  // Clear previous trace
  renderTrace([]);

  // Remove empty state
  const emptyState = chatMessages.querySelector('.chat-empty');
  if (emptyState) emptyState.remove();

  // Add user message
  addMessage('Anda', msg, 'user');
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Show typing indicator
  showTyping();

  try {
    const res = await fetch(`${API_BASE}/complaint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });

    hideTyping();

    if (!res.ok) {
      throw new Error(`Server error: ${res.status}`);
    }

    const data = await res.json();

    // Add final response
    addMessage('Sistem Resolusi', data.response, 'agent');

    // Render trace
    if (data.trace && data.trace.length) {
      renderTrace(data.trace);
      detectActiveAgents(data.trace);
    }
  } catch (err) {
    hideTyping();
    addMessage('Sistem', `Terjadi kesalahan: ${err.message}. Pastikan server FastAPI sedang berjalan.`, 'agent');
  } finally {
    isProcessing = false;
    btnSend.disabled = false;
    chatInput.focus();
  }
}

// --- Add message bubble ---
function addMessage(name, content, type) {
  const msgEl = document.createElement('div');
  msgEl.className = `message ${type === 'user' ? 'user-msg' : 'agent-msg'}`;

  const avatarIcon = type === 'user' ? 'user' : 'bot';
  const avatarClass = type === 'user' ? 'user' : 'agent';
  const tag = type === 'user' ? 'Pelanggan' : 'AI Response';

  msgEl.innerHTML = `
    <div class="message-avatar ${avatarClass}"><i data-lucide="${avatarIcon}" class="icon-sm"></i></div>
    <div class="message-body">
      <div class="message-name" style="color: ${type === 'user' ? 'var(--agent-user)' : 'var(--agent-orchestrator)'}">
        ${name}
        <span class="tag">${tag}</span>
      </div>
      <div class="message-content">${escapeHtml(content)}</div>
    </div>
  `;

  chatMessages.appendChild(msgEl);
  lucide.createIcons({ nodes: [msgEl] });
  scrollToBottom();
}

// --- Typing indicator ---
function showTyping() {
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = 'typingIndicator';
  el.innerHTML = `
    <div class="dots">
      <span></span><span></span><span></span>
    </div>
    <span class="typing-text">Agent-agent sedang berkoordinasi...</span>
  `;
  chatMessages.after(el);
}

function hideTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// --- Trace Rendering ---
function renderTrace(trace) {
  if (!trace.length) {
    traceBody.innerHTML = `
      <div class="trace-empty">
        <div class="trace-empty-icon"><i data-lucide="scan-search" class="icon-lg"></i></div>
        Belum ada trace. Kirim keluhan untuk melihat percakapan antar-agent.
      </div>
    `;
    lucide.createIcons({ nodes: [traceBody] });
    traceCount.textContent = '0';
    return;
  }

  traceCount.textContent = trace.length;
  traceBody.innerHTML = '';

  trace.forEach((msg, i) => {
    const agentName = msg.name || 'Unknown';
    const agentClass = getAgentClass(agentName);
    const content = msg.content || '(no content)';

    const item = document.createElement('div');
    item.className = 'trace-item';
    item.style.animationDelay = `${i * 0.05}s`;
    item.innerHTML = `
      <div class="trace-dot ${agentClass}"></div>
      <div class="trace-info">
        <div class="trace-agent-name ${agentClass}">${escapeHtml(agentName)}</div>
        <div class="trace-content" title="Klik untuk expand">${escapeHtml(content)}</div>
      </div>
    `;

    // Click to expand/collapse
    const traceContent = item.querySelector('.trace-content');
    traceContent.addEventListener('click', () => {
      traceContent.classList.toggle('expanded');
    });

    traceBody.appendChild(item);
  });
}

// --- Detect active agents ---
function detectActiveAgents(trace) {
  activeAgents.clear();
  trace.forEach(msg => {
    const name = (msg.name || '').toLowerCase();
    if (name.includes('orchestrator')) activeAgents.add('orchestrator');
    if (name.includes('logistics')) activeAgents.add('logistics');
    if (name.includes('finance')) activeAgents.add('finance');
    if (name.includes('qa')) activeAgents.add('qa');
  });
  updateAgentBadges();
}

function updateAgentBadges() {
  agentBadges.forEach(badge => {
    const type = badge.dataset.agent;
    if (activeAgents.has(type)) {
      badge.classList.add('active');
    } else {
      badge.classList.remove('active');
    }
  });
}

// --- Helpers ---
function getAgentClass(name) {
  const n = name.toLowerCase();
  if (n.includes('orchestrator')) return 'orchestrator';
  if (n.includes('logistics')) return 'logistics';
  if (n.includes('finance')) return 'finance';
  if (n.includes('qa')) return 'qa';
  if (n.includes('customer') || n.includes('complaint')) return 'user';
  return 'orchestrator';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}
