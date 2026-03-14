/* ================================================================
   app.js — Self-Extending Agent UI
   Handles: chat streaming, skill sidebar, SSE parsing, UI states
   ================================================================ */

const API_BASE = window.location.origin;
const POLL_INTERVAL_MS = 4000;

// ── State ─────────────────────────────────────────────────────────
let isStreaming   = false;
let knownSkills   = new Set();
let currentFilter = 'all';
let pollTimer     = null;
let logCount      = 0;
let logsCollapsed = false;
let allSkillsData = [];

// ── DOM refs ──────────────────────────────────────────────────────
const msgContainer    = document.getElementById('messages-container');
const userInput       = document.getElementById('user-input');
const sendBtn         = document.getElementById('send-btn');
const skillsList      = document.getElementById('skills-list');
const skillsCount     = document.getElementById('skills-count');
const statusDot       = document.getElementById('status-dot');
const statusText      = document.getElementById('status-text');
const toast           = document.getElementById('skill-toast');
const toastSkillName  = document.getElementById('toast-skill-name');
const logList         = document.getElementById('log-list');
const logBadge        = document.getElementById('log-badge');
const learningBanner  = document.getElementById('learning-banner');
const bannerSubText   = document.getElementById('banner-sub-text');

// ── Learning banner steps ─────────────────────────────────────────
const STEPS = ['scan', 'gap', 'learn', 'done'];
const stepEls = {};
STEPS.forEach(s => { stepEls[s] = document.getElementById(`step-${s}`); });

function setStep(step, state) {
  // state: 'active' | 'done' | ''
  const el = stepEls[step];
  if (!el) return;
  el.className = `step-item ${state}`;
}

function activateStep(step) {
  const idx = STEPS.indexOf(step);
  STEPS.forEach((s, i) => {
    if (i < idx)       setStep(s, 'done');
    else if (i === idx) setStep(s, 'active');
    else                setStep(s, '');
  });
}

function completeAllSteps() {
  STEPS.forEach(s => setStep(s, 'done'));
}

function showLearningBanner(msg) {
  learningBanner.classList.add('active');
  if (msg) bannerSubText.textContent = msg;
  setStatus('learning');
}

function hideLearningBanner() {
  learningBanner.classList.remove('active');
}

// ── Logging panel ─────────────────────────────────────────────────
function appendLog(data) {
  if (!logList) return;
  const entry = document.createElement('div');
  entry.className = `log-entry ${data.status || 'info'}`;
  entry.innerHTML = `
    <span class="log-step">[${data.step || 'LOG'}]</span>
    <span class="log-msg">${escapeHtml(data.message || '')}</span>
  `;
  logList.prepend(entry);
  if (logList.children.length > 60) logList.lastElementChild.remove();

  // Update badge
  logCount++;
  if (logsCollapsed) {
    logBadge.style.display = 'inline';
    logBadge.textContent = logCount;
  }

  // Map step name → progress
  const step = (data.step || '').toLowerCase();
  if (step === 'scan')  activateStep('scan');
  if (step === 'gap')   activateStep('gap');
  if (step === 'learn') activateStep('learn');
  if (step === 'ready' || step === 'done') {
    completeAllSteps();
    setTimeout(() => hideLearningBanner(), 1800);
  }
}

function toggleLogs() {
  const panel = document.getElementById('orchestrator-logs');
  logsCollapsed = !logsCollapsed;
  panel.classList.toggle('collapsed', logsCollapsed);
  if (!logsCollapsed) {
    logBadge.style.display = 'none';
    logCount = 0;
  }
}

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setStatus('connecting');
  checkHealth();
  refreshSkills();
  startPolling();
});

// ── Health check ──────────────────────────────────────────────────
async function checkHealth() {
  try {
    const resp = await fetch(`${API_BASE}/api/health`);
    setStatus(resp.ok ? 'online' : 'error');
  } catch {
    setStatus('error');
  }
}

function setStatus(state) {
  statusDot.className = 'status-dot';
  if (state === 'online') {
    statusDot.classList.add('online');
    statusText.textContent = 'Agent ready';
  } else if (state === 'error') {
    statusDot.classList.add('error');
    statusText.textContent = 'Offline';
  } else if (state === 'learning') {
    statusDot.classList.add('learning');
    statusText.textContent = 'Learning…';
  } else {
    statusText.textContent = 'Connecting…';
  }
}

// ── Skills sidebar ────────────────────────────────────────────────
async function refreshSkills() {
  try {
    const resp = await fetch(`${API_BASE}/api/skills`);
    if (!resp.ok) return;
    const data = await resp.json();
    allSkillsData = data.skills || [];
    renderSkills(allSkillsData);
  } catch (e) {
    console.warn('Skills fetch failed:', e);
  }
}

function renderSkills(skills) {
  const prevCount = knownSkills.size;
  const newlyAdded = [];

  skills.forEach(s => {
    if (!knownSkills.has(s.name)) {
      if (prevCount > 0) newlyAdded.push(s);
      knownSkills.add(s.name);
    }
  });

  // Animate count badge
  const countEl = document.getElementById('skills-count');
  countEl.textContent = skills.length;
  if (newlyAdded.length > 0) {
    countEl.classList.add('bump');
    setTimeout(() => countEl.classList.remove('bump'), 400);
  }

  const filtered = currentFilter === 'all'
    ? skills
    : skills.filter(s => s.type === currentFilter);

  if (filtered.length === 0) {
    skillsList.innerHTML = `
      <div class="skills-empty">
        <div class="skills-empty-icon">📭</div>
        <span>No ${currentFilter === 'all' ? '' : currentFilter + ' '}skills yet</span>
      </div>`;
    return;
  }

  skillsList.innerHTML = filtered.map(skill => buildSkillCard(skill, newlyAdded)).join('');

  // Show toast for newly generated skills
  newlyAdded.filter(s => s.type === 'generated').forEach(s => showSkillToast(s.name));
}

function buildSkillCard(skill, newlyAdded) {
  const isNew = newlyAdded.some(s => s.name === skill.name);
  const badgeClass = skill.type === 'generated' ? 'badge-generated' : 'badge-builtin';
  const badgeLabel = skill.type === 'generated' ? '⚡ Generated' : '✓ Built-in';
  const time = formatRelativeTime(skill.created_at);
  const desc = skill.description
    ? escapeHtml(skill.description).substring(0, 120) + (skill.description.length > 120 ? '…' : '')
    : 'No description available.';

  return `
    <div class="skill-card ${isNew ? 'new-skill' : ''}" id="skill-${escapeId(skill.name)}"
         onclick="insertSkillPrompt('${escapeAttr(skill.name)}')">
      <div class="skill-card-header">
        <div class="skill-card-name">${escapeHtml(skill.name)}</div>
        <span class="skill-badge ${badgeClass}">${badgeLabel}</span>
      </div>
      <div class="skill-card-desc">${desc}</div>
      <div class="skill-card-footer">
        <span class="skill-card-time">${time}</span>
      </div>
    </div>`;
}

function insertSkillPrompt(skillName) {
  userInput.value = `Use the ${skillName} skill to help me with `;
  userInput.focus();
  autoResize(userInput);
}

function filterSkills(filter, btn) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderSkills(allSkillsData);
}

// ── Polling ───────────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(async () => {
    if (isStreaming) return; // Skip poll during active stream
    try {
      const resp = await fetch(`${API_BASE}/api/skills`);
      if (!resp.ok) return;
      const data = await resp.json();
      allSkillsData = data.skills || [];
      renderSkills(allSkillsData);
    } catch { /* silent */ }
  }, POLL_INTERVAL_MS);
}

// ── Toast ─────────────────────────────────────────────────────────
function showSkillToast(skillName) {
  toastSkillName.textContent = skillName;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 5000);
}

// ── SSE Stream Parsing ────────────────────────────────────────────
/**
 * Properly parses SSE stream from a ReadableStream reader.
 * Handles the case where event: and data: arrive in different chunks.
 * SSE spec: blank line separates events; event type + data lines form one block.
 */
async function* parseSseStream(reader) {
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Process complete events (separated by \n\n)
    let boundary;
    while ((boundary = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      if (!block.trim()) continue;

      const lines = block.split('\n');
      let eventType = 'message';
      let dataLines = [];

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          dataLines.push(line.slice(6));
        }
      }

      if (dataLines.length > 0) {
        yield { event: eventType, data: dataLines.join('\n') };
      }
    }
  }
}

// ── Chat ──────────────────────────────────────────────────────────
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isStreaming) return;

  // Hide welcome screen
  const ws = document.getElementById('welcome-screen');
  if (ws) ws.style.display = 'none';

  appendMessage('user', text);
  userInput.value = '';
  autoResize(userInput);

  // Lock UI
  isStreaming     = true;
  sendBtn.disabled = true;

  // Agent thinking bubble
  const agentMsgId = 'msg-' + Date.now();
  appendMessage('agent', '', agentMsgId);
  const bodyEl = document.getElementById(agentMsgId);
  bodyEl.innerHTML = `<div class="thinking-dots"><span></span><span></span><span></span></div>`;

  let fullText     = '';
  let isFirstChunk = true;
  let inLearning   = false;

  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (!resp.ok) throw new Error(`Server error ${resp.status}`);

    const reader = resp.body.getReader();

    for await (const { event, data } of parseSseStream(reader)) {

      // ── Handle each SSE event type ────────────────────────────
      switch (event) {

        case 'log':
          try {
            const logData = JSON.parse(data);
            appendLog(logData);
          } catch { /* ignore bad JSON */ }
          break;

        case 'learning':
          if (data === 'start') {
            inLearning = true;
            showLearningBanner('Researching and writing new skill…');
            activateStep('gap');
            // Show learning indicator in the chat bubble
            if (isFirstChunk) {
              bodyEl.innerHTML = `
                <div class="learning-indicator">
                  <div class="learning-ring"></div>
                  <span>Skill gap detected — building new skill module…</span>
                </div>`;
              isFirstChunk = false;
            }
          } else if (data === 'failed') {
            hideLearningBanner();
            inLearning = false;
          }
          break;

        case 'thinking':
          // Re-show thinking dots when switching to answering phase
          if (inLearning && isFirstChunk) {
            bodyEl.innerHTML = `<div class="thinking-dots"><span></span><span></span><span></span></div>`;
          }
          break;

        case 'skill_created':
        case 'skill_integrated':
          setTimeout(() => refreshSkills(), 500);
          try {
            const payload = JSON.parse(data);
            const sName = payload.name || 'new-skill';
            appendLog({ step: 'Skill', status: 'success', message: `✅ Skill '${sName}' created and loaded!` });
          } catch { /* ignore */ }
          break;

        case 'message':
          if (data === '[DONE]') break;
          if (isFirstChunk) {
            bodyEl.innerHTML = '';
            isFirstChunk = false;
          }
          fullText += data;
          bodyEl.innerHTML = renderMarkdown(fullText) + '<span class="cursor-blink"></span>';
          scrollToBottom();
          break;

        case 'done':
          inLearning = false;
          hideLearningBanner();
          break;

        case 'error':
          bodyEl.innerHTML = `<span style="color:#f87171">⚠ ${escapeHtml(data)}</span>`;
          break;
      }
    }

    // Finalize
    bodyEl.innerHTML = renderMarkdown(fullText || '*(No response)*');

  } catch (err) {
    bodyEl.innerHTML = `<span style="color:#f87171">⚠ Error: ${escapeHtml(err.message)}</span>`;
    hideLearningBanner();
  } finally {
    isStreaming      = false;
    sendBtn.disabled = false;
    scrollToBottom();
    setStatus('online');
    // Final skill refresh
    setTimeout(() => refreshSkills(), 1000);
  }
}

function appendMessage(role, text, bodyId) {
  const msgEl = document.createElement('div');
  msgEl.className = `message message-${role}`;

  const avatarContent = role === 'user' ? 'U' : role === 'system' ? '⚡' : 'AI';
  const roleName      = role === 'user' ? 'You' : role === 'system' ? 'System' : 'Dev Assistant';
  const idAttr        = bodyId ? `id="${bodyId}"` : '';

  msgEl.innerHTML = `
    <div class="message-header">
      <div class="avatar avatar-${role}">${avatarContent}</div>
      <span class="message-role">${roleName}</span>
    </div>
    <div class="message-body" ${idAttr}>${escapeHtml(text)}</div>`;

  msgContainer.appendChild(msgEl);
  scrollToBottom();
  return msgEl;
}

function clearChat() {
  // Reset learning state
  hideLearningBanner();
  STEPS.forEach(s => setStep(s, ''));
  fullText = '';

  msgContainer.innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <div class="welcome-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
        </svg>
      </div>
      <h2 class="welcome-title">How can I help you?</h2>
      <p class="welcome-sub">I'm a self-extending assistant. Ask me to review code, guide Git workflows — or create a brand new skill.</p>
      <div class="quick-prompts">
        <button class="quick-btn" onclick="useQuickPrompt(this)"><span class="quick-icon">🔍</span><span>Review this code for security issues</span></button>
        <button class="quick-btn" onclick="useQuickPrompt(this)"><span class="quick-icon">🌿</span><span>Guide me through Git branching strategy</span></button>
        <button class="quick-btn" onclick="useQuickPrompt(this)"><span class="quick-icon">⚡</span><span>Create a new skill for Docker + FastAPI</span></button>
        <button class="quick-btn" onclick="useQuickPrompt(this)"><span class="quick-icon">📝</span><span>Write a skill for Python testing best practices</span></button>
      </div>
    </div>`;
}

// ── Quick prompts ─────────────────────────────────────────────────
function useQuickPrompt(btn) {
  const text = btn.querySelector('span:last-child').textContent;
  userInput.value = text;
  userInput.focus();
  autoResize(userInput);
}

// ── Keyboard ──────────────────────────────────────────────────────
function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ── Auto-resize textarea ──────────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

// ── Scroll ────────────────────────────────────────────────────────
function scrollToBottom() {
  msgContainer.scrollTop = msgContainer.scrollHeight;
}

// ── Markdown renderer ─────────────────────────────────────────────
function renderMarkdown(text) {
  // If the LLM wraps its entire response in a ```markdown ... ``` fence, unwrap it.
  // This prevents the whole answer from rendering as a raw code block.
  const outerFenceMatch = text.match(/^```(?:markdown|md)?\s*\n?([\s\S]*?)\n?```\s*$/i);
  if (outerFenceMatch) {
    text = outerFenceMatch[1].trim();
  }

  let html = escapeHtml(text);

  // Fenced code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold & italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g,          '<em>$1</em>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3 style="color:var(--accent-cyan);font-size:13px;margin:12px 0 5px;font-weight:700">$1</h3>');
  html = html.replace(/^## (.+)$/gm,  '<h2 style="color:var(--accent-purple);font-size:15px;margin:14px 0 6px;font-weight:700">$1</h2>');
  html = html.replace(/^# (.+)$/gm,   '<h1 style="color:var(--text-primary);font-size:17px;margin:16px 0 8px;font-weight:700">$1</h1>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--border-subtle);margin:14px 0">');

  // Unordered lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li style="margin:3px 0;padding-left:4px">$1</li>');
  html = html.replace(/(<li[\s\S]*?<\/li>)/g, '<ul style="margin:8px 0;padding-left:22px">$1</ul>');

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li style="margin:3px 0;padding-left:4px">$1</li>');

  // Newlines → breaks (but not inside pre)
  html = html.replace(/\n/g, '<br>');

  // Fix pre blocks after \n replacement
  html = html.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/g, (_, code) => {
    return `<pre><code>${code.replace(/<br>/g, '\n')}</code></pre>`;
  });

  return html;
}

// ── Helpers ───────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return String(str).replace(/'/g, "\\'");
}

function escapeId(str) {
  return String(str).replace(/[^a-z0-9-]/gi, '-');
}

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const diffMs  = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1)  return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24)  return `${diffHr}h ago`;
  return date.toLocaleDateString();
}
