// ============================================
// BelanjaPintar E-Commerce — Chat Widget Logic
// ============================================

const API_BASE = window.location.origin;

// --- DOM ---
const chatFab = document.getElementById('chatFab');
const chatWidget = document.getElementById('chatWidget');
const cwClose = document.getElementById('cwClose');
const cwMessages = document.getElementById('cwMessages');
const cwInput = document.getElementById('cwInput');
const cwSend = document.getElementById('cwSend');
const cwQuickActions = document.getElementById('cwQuickActions');
const aiBannerBtn = document.getElementById('aiBannerBtn');

// --- State ---
let isOpen = false;
let isProcessing = false;
let hasGreeted = false;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  chatFab.addEventListener('click', toggleChat);
  cwClose.addEventListener('click', toggleChat);

  cwSend.addEventListener('click', sendMessage);
  cwInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  cwInput.addEventListener('input', () => {
    cwInput.style.height = 'auto';
    cwInput.style.height = Math.min(cwInput.scrollHeight, 100) + 'px';
  });

  // Quick action buttons
  document.querySelectorAll('.cw-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (!isProcessing) {
        cwInput.value = btn.dataset.message;
        cwInput.focus();
      }
    });
  });

  // AI banner button
  if (aiBannerBtn) {
    aiBannerBtn.addEventListener('click', () => {
      if (!isOpen) toggleChat();
    });
  }

  // Order complaint buttons
  document.querySelectorAll('.order-complaint-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const msg = btn.dataset.complaint;
      if (msg) {
        if (!isOpen) toggleChat();
        setTimeout(() => {
          cwInput.value = msg;
          cwInput.focus();
        }, 400);
      }
    });
  });
});

// --- Toggle Chat ---
function toggleChat() {
  isOpen = !isOpen;

  if (isOpen) {
    chatWidget.classList.add('open');
    chatFab.classList.add('hidden');
    cwInput.focus();
    if (!hasGreeted) {
      showGreeting();
      hasGreeted = true;
    }
  } else {
    chatWidget.classList.remove('open');
    chatFab.classList.remove('hidden');
  }
}

// --- Greeting ---
function showGreeting() {
  setTimeout(() => {
    addBotMessage(
      'Halo! Selamat datang di BelanjaPintar. 👋\n\n' +
      'Saya adalah AI Customer Service yang siap membantu Anda menyelesaikan keluhan terkait:\n\n' +
      '• Pengiriman & logistik\n' +
      '• Pembayaran & refund\n' +
      '• Kualitas produk\n\n' +
      'Silakan ketik keluhan Anda atau gunakan tombol aksi cepat di bawah.'
    );
  }, 300);
}

// --- Send Message ---
async function sendMessage() {
  const msg = cwInput.value.trim();
  if (!msg || isProcessing) return;

  isProcessing = true;
  cwSend.disabled = true;
  hideQuickActions();

  addUserMessage(msg);
  cwInput.value = '';
  cwInput.style.height = 'auto';

  showTyping();

  try {
    const res = await fetch(`${API_BASE}/complaint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });

    hideTyping();

    if (!res.ok) throw new Error(`Error ${res.status}`);

    const data = await res.json();
    addBotMessage(data.response);

    // Show agent info if available
    if (data.trace && data.trace.length > 1) {
      const agents = new Set();
      data.trace.forEach(m => {
        const n = (m.name || '').toLowerCase();
        if (n.includes('logistics')) agents.add('Logistics');
        if (n.includes('finance')) agents.add('Finance');
        if (n.includes('qa')) agents.add('QA');
      });
      if (agents.size > 0) {
        addSystemMessage(`Ditangani oleh: ${[...agents].join(', ')} Agent`);
      }
    }
  } catch (err) {
    hideTyping();
    addBotMessage('Maaf, terjadi kesalahan saat menghubungi sistem. Silakan coba lagi nanti.');
  } finally {
    isProcessing = false;
    cwSend.disabled = false;
    cwInput.focus();
    showQuickActions();
  }
}

// --- Message Helpers ---
function addUserMessage(text) {
  const el = document.createElement('div');
  el.className = 'cw-msg user';
  el.innerHTML = `
    <div class="cw-msg-avatar"><i data-lucide="user" style="width:14px;height:14px"></i></div>
    <div class="cw-msg-bubble">${escapeHtml(text)}</div>
  `;
  cwMessages.appendChild(el);
  lucide.createIcons({ nodes: [el] });
  scrollBottom();
}

function addBotMessage(text) {
  const el = document.createElement('div');
  el.className = 'cw-msg bot';
  el.innerHTML = `
    <div class="cw-msg-avatar"><i data-lucide="bot" style="width:14px;height:14px"></i></div>
    <div class="cw-msg-bubble">${escapeHtml(text)}</div>
  `;
  cwMessages.appendChild(el);
  lucide.createIcons({ nodes: [el] });
  scrollBottom();
}

function addSystemMessage(text) {
  const el = document.createElement('div');
  el.style.cssText = 'text-align:center;padding:4px 0;';
  el.innerHTML = `<span style="font-size:0.7rem;color:#6B6B80;background:rgba(124,58,237,0.08);padding:3px 12px;border-radius:20px;">${escapeHtml(text)}</span>`;
  cwMessages.appendChild(el);
  scrollBottom();
}

// --- Typing ---
function showTyping() {
  const el = document.createElement('div');
  el.className = 'cw-typing';
  el.id = 'cwTyping';
  el.innerHTML = `
    <div class="cw-typing-dots"><span></span><span></span><span></span></div>
    <span class="cw-typing-text">AI sedang menganalisis...</span>
  `;
  cwMessages.appendChild(el);
  scrollBottom();
}

function hideTyping() {
  const el = document.getElementById('cwTyping');
  if (el) el.remove();
}

// --- Quick Actions ---
function hideQuickActions() {
  if (cwQuickActions) cwQuickActions.style.display = 'none';
}

function showQuickActions() {
  if (cwQuickActions) cwQuickActions.style.display = 'flex';
}

// --- Helpers ---
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function scrollBottom() {
  requestAnimationFrame(() => {
    cwMessages.scrollTop = cwMessages.scrollHeight;
  });
}
