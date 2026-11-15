/**
 * Aevora AI — NovaCare Staff Dashboard Client Application
 * Connects to real backend endpoints under /api/v1/staff/...
 */

const API_BASE = '/api/v1/staff';

const state = {
  token: localStorage.getItem('aevora_token') || '',
  currentUser: null,
  activeTab: 'overview',
  activeConversationId: null,
};

// =============================================================================
// HTTP Client with Auth Interceptor
// =============================================================================

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Token expired or unauthorized
    handleLogout('Session expired. Please sign in again.');
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return res.json();
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

// =============================================================================
// Authentication Lifecycle
// =============================================================================

async function checkAuthSession() {
  if (!state.token) {
    showLoginModal();
    return;
  }

  try {
    const user = await apiFetch('/auth/me');
    state.currentUser = user;
    showMainLayout();
    initDashboard();
  } catch (err) {
    showLoginModal();
  }
}

function showLoginModal() {
  document.getElementById('loginModal').style.display = 'flex';
  document.getElementById('mainLayout').style.display = 'none';
  document.getElementById('staffProfile').style.display = 'none';
}

function showMainLayout() {
  document.getElementById('loginModal').style.display = 'none';
  document.getElementById('mainLayout').style.display = 'flex';
  document.getElementById('staffProfile').style.display = 'flex';

  if (state.currentUser) {
    document.getElementById('staffName').innerText = state.currentUser.full_name || state.currentUser.username;
    document.getElementById('staffRole').innerText = state.currentUser.role || 'Staff';
    const initials = (state.currentUser.full_name || 'NC').split(' ').map(n => n[0]).join('').substring(0, 2);
    document.getElementById('staffAvatar').innerText = initials.toUpperCase();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById('usernameInput');
  const passwordInput = document.getElementById('passwordInput');
  const errorBox = document.getElementById('loginError');
  const submitBtn = document.getElementById('loginSubmitBtn');

  errorBox.style.display = 'none';
  submitBtn.disabled = true;
  submitBtn.innerText = 'Verifying credentials...';

  try {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });

    state.token = data.access_token;
    localStorage.setItem('aevora_token', data.access_token);
    state.currentUser = {
      username: data.username,
      full_name: data.full_name,
      role: data.role,
    };

    showMainLayout();
    initDashboard();
    showToast(`Welcome, ${data.full_name || data.username}`);
  } catch (err) {
    errorBox.innerText = err.message;
    errorBox.style.display = 'block';
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerText = 'Sign In to Dashboard';
  }
}

function handleLogout(message = 'Logged out successfully.') {
  state.token = '';
  state.currentUser = null;
  localStorage.removeItem('aevora_token');
  showLoginModal();
  showToast(message, 'info');
}

// =============================================================================
// Tab Switching
// =============================================================================

function setupNavigation() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      switchTab(tab);
    });
  });

  // Action links like "View all ->"
  document.querySelectorAll('[data-goto]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = link.getAttribute('data-goto');
      switchTab(target);
    });
  });
}

function switchTab(tabName) {
  state.activeTab = tabName;

  document.querySelectorAll('.nav-item').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  document.querySelectorAll('.tab-pane').forEach(pane => {
    if (pane.id === `pane-${tabName}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // Load relevant data on tab entry
  if (tabName === 'overview') loadOverview();
  if (tabName === 'conversations') loadConversations();
  if (tabName === 'appointments') loadAppointments();
  if (tabName === 'handoffs') loadHandoffs();
  if (tabName === 'knowledge') loadKnowledgeBase();
  if (tabName === 'system') loadSystemHealth();
}

// =============================================================================
// Section: Overview
// =============================================================================

async function loadOverview() {
  try {
    const data = await apiFetch('/overview');

    document.getElementById('metricTotalConvs').innerText = data.total_conversations;
    document.getElementById('metricActiveConvs').innerText = data.active_conversations;
    document.getElementById('metricPendingAppts').innerText = data.pending_appointments;
    document.getElementById('metricConfirmedAppts').innerText = data.confirmed_appointments;
    document.getElementById('metricPendingHandoffs').innerText = data.pending_handoffs;
    document.getElementById('metricResolvedHandoffs').innerText = data.resolved_handoffs;
    document.getElementById('metricTotalMessages').innerText = data.total_messages;
    document.getElementById('metricWhatsAppEvents').innerText = data.whatsapp_events_count;

    // Badges in sidebar
    const apptBadge = document.getElementById('navApptBadge');
    if (data.pending_appointments > 0) {
      apptBadge.innerText = data.pending_appointments;
      apptBadge.style.display = 'inline-flex';
    } else {
      apptBadge.style.display = 'none';
    }

    const handoffBadge = document.getElementById('navHandoffBadge');
    if (data.pending_handoffs > 0) {
      handoffBadge.innerText = data.pending_handoffs;
      handoffBadge.style.display = 'inline-flex';
    } else {
      handoffBadge.style.display = 'none';
    }

    document.getElementById('navConvCount').innerText = data.total_conversations;

    // Load recent mini lists
    loadOverviewMiniLists();
  } catch (err) {
    showToast(`Failed to load overview: ${err.message}`, 'error');
  }
}

async function loadOverviewMiniLists() {
  try {
    const appts = await apiFetch('/appointments?status=pending_staff_confirmation&limit=3');
    const apptList = document.getElementById('overviewApptsList');
    if (appts.length === 0) {
      apptList.innerHTML = '<div class="empty-state py-2">No pending appointments awaiting review.</div>';
    } else {
      apptList.innerHTML = appts.map(a => `
        <div class="compact-item">
          <div>
            <strong>${escapeHtml(a.patient_name)}</strong>
            <span style="color:var(--color-text-muted); font-size:12px;"> &bull; ${escapeHtml(a.doctor_name || 'General')}</span>
            <div style="font-size:11px; color:var(--color-text-muted);">${escapeHtml(a.preferred_date)} at ${escapeHtml(a.preferred_time)}</div>
          </div>
          <span class="badge badge-coral">Pending</span>
        </div>
      `).join('');
    }

    const handoffs = await apiFetch('/handoffs?status=pending&limit=3');
    const handoffList = document.getElementById('overviewHandoffsList');
    if (handoffs.length === 0) {
      handoffList.innerHTML = '<div class="empty-state py-2">No pending staff handoffs.</div>';
    } else {
      handoffList.innerHTML = handoffs.map(h => `
        <div class="compact-item">
          <div>
            <strong>Reason: ${escapeHtml(h.reason)}</strong>
            <div style="font-size:11px; color:var(--color-text-muted);">${escapeHtml(h.summary.substring(0, 50))}...</div>
          </div>
          <span class="badge badge-gold">Escalated</span>
        </div>
      `).join('');
    }
  } catch (_) {}
}

// =============================================================================
// Section: Conversations
// =============================================================================

async function loadConversations() {
  const masterContainer = document.getElementById('convMasterList');
  const search = document.getElementById('convSearchInput').value.trim();
  const channel = document.getElementById('convChannelSelect').value;

  let query = '/conversations?limit=50';
  if (search) query += `&search=${encodeURIComponent(search)}`;
  if (channel) query += `&channel=${encodeURIComponent(channel)}`;

  try {
    masterContainer.innerHTML = '<div class="empty-state">Loading conversations...</div>';
    const convs = await apiFetch(query);

    if (convs.length === 0) {
      masterContainer.innerHTML = '<div class="empty-state">No conversations found.</div>';
      return;
    }

    masterContainer.innerHTML = convs.map(c => {
      const activeClass = state.activeConversationId === c.id ? 'active' : '';
      const dateStr = formatDateTime(c.last_message_at);
      const phone = c.external_user_id || 'Anonymous';
      const preview = c.last_message_text || '(No messages yet)';
      const langBadge = formatLangBadge(c.preferred_language);
      const channelBadge = c.channel === 'whatsapp' ? '<span class="badge badge-teal">WhatsApp</span>' : '<span class="badge badge-navy">Web</span>';

      return `
        <div class="conv-master-item ${activeClass}" data-id="${c.id}">
          <div class="conv-item-top">
            <span class="conv-item-sender">${escapeHtml(phone)}</span>
            <span class="conv-item-time">${dateStr}</span>
          </div>
          <div class="conv-item-preview">${escapeHtml(preview)}</div>
          <div class="conv-item-tags">
            ${channelBadge}
            ${langBadge}
            <span class="badge badge-subtle">${c.message_count} msgs</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners
    masterContainer.querySelectorAll('.conv-master-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.getAttribute('data-id');
        selectConversation(id);
      });
    });

    // If an active conversation is already selected or default to first
    if (!state.activeConversationId && convs.length > 0) {
      selectConversation(convs[0].id);
    }
  } catch (err) {
    masterContainer.innerHTML = `<div class="empty-state error">Failed to load: ${escapeHtml(err.message)}</div>`;
  }
}

async function selectConversation(convId) {
  state.activeConversationId = convId;

  // Highlight master list
  document.querySelectorAll('.conv-master-item').forEach(item => {
    if (item.getAttribute('data-id') === convId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  const detailContainer = document.getElementById('convDetailView');
  detailContainer.innerHTML = '<div class="empty-state">Loading conversation details...</div>';

  try {
    const detail = await apiFetch(`/conversations/${convId}`);

    const headerHtml = `
      <div class="conv-detail-header">
        <div>
          <h3 style="font-size:14px; font-weight:700; color:var(--color-navy);">${escapeHtml(detail.external_user_id)}</h3>
          <p style="font-size:11px; color:var(--color-text-muted);">
            ID: <code>${detail.id}</code> &bull; Channel: <strong>${detail.channel.toUpperCase()}</strong> &bull; Language: <strong>${detail.preferred_language}</strong>
          </p>
        </div>
        <div>
          <span class="badge badge-teal">${detail.status.toUpperCase()}</span>
        </div>
      </div>
    `;

    const messagesHtml = detail.messages.map(m => {
      const isUrdu = m.language === 'ur';
      const roleClass = m.role === 'user' ? 'user' : 'assistant';
      const urduClass = isUrdu ? 'urdu' : '';
      const timeStr = formatDateTime(m.created_at);

      let citationsHtml = '';
      if (m.citations && m.citations.length > 0) {
        citationsHtml = `
          <div class="citation-list">
            <strong>Sources:</strong>
            ${m.citations.map(c => `
              <span class="citation-item">Page ${c.page || 'Doc'}: ${escapeHtml(c.section || c.source)}</span>
            `).join('')}
          </div>
        `;
      }

      return `
        <div class="chat-bubble ${roleClass} ${urduClass}">
          <div class="bubble-content">${escapeHtml(m.content)}</div>
          ${citationsHtml}
          <div class="bubble-meta">
            <span>${m.role === 'user' ? 'Patient' : 'Aevora AI'} &bull; ${m.intent || 'general'}</span>
            <span>${timeStr}</span>
          </div>
        </div>
      `;
    }).join('');

    detailContainer.innerHTML = `
      ${headerHtml}
      <div class="conv-detail-body">${messagesHtml}</div>
    `;

    // Scroll to bottom
    const bodyEl = detailContainer.querySelector('.conv-detail-body');
    if (bodyEl) bodyEl.scrollTop = bodyEl.scrollHeight;
  } catch (err) {
    detailContainer.innerHTML = `<div class="empty-state error">Failed to load conversation: ${escapeHtml(err.message)}</div>`;
  }
}

// =============================================================================
// Section: Appointments
// =============================================================================

async function loadAppointments() {
  const tbody = document.getElementById('apptsTableBody');
  const filter = document.getElementById('apptFilterSelect').value;

  let query = '/appointments?limit=100';
  if (filter) query += `&status=${encodeURIComponent(filter)}`;

  try {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Loading appointments...</td></tr>';
    const appts = await apiFetch(query);

    if (appts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">No appointments found matching filter.</td></tr>';
      return;
    }

    tbody.innerHTML = appts.map(a => {
      const statusBadge = formatApptStatus(a.status);
      const isPending = a.status === 'pending_staff_confirmation';

      return `
        <tr>
          <td><strong>${escapeHtml(a.patient_name)}</strong></td>
          <td>${escapeHtml(a.doctor_name || 'General OPD')}</td>
          <td>${escapeHtml(a.preferred_date)} at ${escapeHtml(a.preferred_time)}</td>
          <td><code>${escapeHtml(a.callback_number || 'N/A')}</code></td>
          <td>${statusBadge}</td>
          <td style="font-size:11px; color:var(--color-text-muted);">${formatDateTime(a.created_at)}</td>
          <td class="text-right">
            ${isPending ? `
              <button class="btn btn-primary btn-sm" onclick="updateApptStatus('${a.id}', 'confirmed_by_staff')">Confirm</button>
              <button class="btn btn-coral btn-sm" onclick="updateApptStatus('${a.id}', 'cancelled')">Cancel</button>
            ` : `
              <select class="form-control form-control-sm" style="display:inline-block; width:auto;" onchange="updateApptStatus('${a.id}', this.value)">
                <option value="${a.status}" selected>Change...</option>
                <option value="confirmed_by_staff">Confirm</option>
                <option value="reviewed">Reviewed</option>
                <option value="cancelled">Cancel</option>
              </select>
            `}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Error: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function updateApptStatus(apptId, newStatus) {
  try {
    await apiFetch(`/appointments/${apptId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    showToast(`Appointment status updated to '${newStatus}'.`);
    loadAppointments();
    loadOverview();
  } catch (err) {
    showToast(`Failed to update status: ${err.message}`, 'error');
  }
}

// =============================================================================
// Section: Staff Handoffs
// =============================================================================

async function loadHandoffs() {
  const tbody = document.getElementById('handoffsTableBody');
  const filter = document.getElementById('handoffFilterSelect').value;

  let query = '/handoffs?limit=100';
  if (filter) query += `&status=${encodeURIComponent(filter)}`;

  try {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Loading handoffs...</td></tr>';
    const handoffs = await apiFetch(query);

    if (handoffs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No handoffs found matching filter.</td></tr>';
      return;
    }

    tbody.innerHTML = handoffs.map(h => {
      const isPending = h.status === 'pending';
      const statusBadge = h.status === 'pending'
        ? '<span class="badge badge-coral">Pending</span>'
        : (h.status === 'in_progress' ? '<span class="badge badge-gold">In Progress</span>' : '<span class="badge badge-teal">Resolved</span>');

      return `
        <tr>
          <td><code>${escapeHtml(h.id.substring(0, 8))}...</code></td>
          <td><strong>${escapeHtml(h.reason)}</strong></td>
          <td>${escapeHtml(h.summary)}</td>
          <td>${statusBadge}</td>
          <td style="font-size:11px; color:var(--color-text-muted);">${formatDateTime(h.created_at)}</td>
          <td class="text-right">
            ${isPending ? `
              <button class="btn btn-secondary btn-sm" onclick="updateHandoffStatus('${h.id}', 'in_progress')">Take Over</button>
              <button class="btn btn-primary btn-sm" onclick="updateHandoffStatus('${h.id}', 'resolved')">Resolve</button>
            ` : `
              <button class="btn btn-secondary btn-sm" onclick="updateHandoffStatus('${h.id}', 'resolved')">Mark Resolved</button>
            `}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-danger">Error: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function updateHandoffStatus(handoffId, newStatus) {
  try {
    await apiFetch(`/handoffs/${handoffId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    showToast(`Handoff updated to '${newStatus}'.`);
    loadHandoffs();
    loadOverview();
  } catch (err) {
    showToast(`Failed to update handoff: ${err.message}`, 'error');
  }
}

// =============================================================================
// Section: Knowledge Base
// =============================================================================

async function loadKnowledgeBase() {
  try {
    const data = await apiFetch('/knowledge-base/status');
    document.getElementById('kbChunkCount').innerText = data.indexed_chunks;
    document.getElementById('kbConsistencyCount').innerText = data.consistency_notes_count;
  } catch (err) {
    showToast(`Failed to load KB metadata: ${err.message}`, 'error');
  }
}

// =============================================================================
// Section: System Diagnostics
// =============================================================================

async function loadSystemHealth() {
  const container = document.getElementById('systemDiagnosticsGrid');
  try {
    container.innerHTML = '<div>Loading diagnostics...</div>';
    const sys = await apiFetch('/system/status');

    container.innerHTML = `
      <div class="diag-card">
        <span class="diag-label">FastAPI Service</span>
        <span class="diag-value">
          <span class="status-dot green"></span>
          ${sys.fastapi_status} (v${sys.version})
        </span>
      </div>

      <div class="diag-card">
        <span class="diag-label">Google Gemini AI</span>
        <span class="diag-value">
          <span class="status-dot ${sys.gemini_status.includes('Connected') ? 'green' : 'red'}"></span>
          ${sys.gemini_status}
        </span>
        <span style="font-size:11px; color:var(--color-text-muted);">Model: <code>${sys.gemini_model}</code></span>
      </div>

      <div class="diag-card">
        <span class="diag-label">WhatsApp Cloud API</span>
        <span class="diag-value">
          <span class="status-dot ${sys.whatsapp_status.includes('Connected') ? 'green' : 'red'}"></span>
          ${sys.whatsapp_status}
        </span>
        <span style="font-size:11px; color:var(--color-text-muted);">Phone ID: <code>${sys.whatsapp_phone_number_id || 'Not set'}</code></span>
      </div>

      <div class="diag-card">
        <span class="diag-label">Durable Event Worker</span>
        <span class="diag-value">
          <span class="status-dot ${sys.worker_status === 'Running' ? 'green' : 'red'}"></span>
          ${sys.worker_status}
        </span>
      </div>

      <div class="diag-card">
        <span class="diag-label">RAG Hybrid Vector Store</span>
        <span class="diag-value">
          <span class="status-dot ${sys.rag_status.includes('Ready') ? 'green' : 'red'}"></span>
          ${sys.rag_status}
        </span>
      </div>

      <div class="diag-card">
        <span class="diag-label">Faster-Whisper Transcription</span>
        <span class="diag-value">
          <span class="status-dot green"></span>
          ${sys.whisper_status}
        </span>
        <span style="font-size:11px; color:var(--color-text-muted);">Device target: <code>${sys.whisper_device}</code></span>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Failed to load system diagnostics: ${escapeHtml(err.message)}</div>`;
  }
}

// =============================================================================
// Formatters & Utility Helpers
// =============================================================================

function formatDateTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
}

function formatLangBadge(lang) {
  if (lang === 'ur') return '<span class="badge badge-gold">اردو</span>';
  if (lang === 'roman_ur') return '<span class="badge badge-teal">Roman Urdu</span>';
  return '<span class="badge badge-navy">English</span>';
}

function formatApptStatus(status) {
  if (status === 'pending_staff_confirmation') return '<span class="badge badge-coral">Pending Confirmation</span>';
  if (status === 'confirmed_by_staff') return '<span class="badge badge-teal">Confirmed by Staff</span>';
  if (status === 'cancelled') return '<span class="badge badge-subtle">Cancelled</span>';
  return `<span class="badge badge-gold">${escapeHtml(status)}</span>`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function initDashboard() {
  setupNavigation();
  loadOverview();

  // Attach search & filters
  document.getElementById('convSearchInput')?.addEventListener('input', debounce(loadConversations, 300));
  document.getElementById('convChannelSelect')?.addEventListener('change', loadConversations);
  document.getElementById('apptFilterSelect')?.addEventListener('change', loadAppointments);
  document.getElementById('handoffFilterSelect')?.addEventListener('change', loadHandoffs);

  // Manual refresh buttons
  document.getElementById('refreshOverviewBtn')?.addEventListener('click', loadOverview);
  document.getElementById('refreshApptsBtn')?.addEventListener('click', loadAppointments);
  document.getElementById('refreshHandoffsBtn')?.addEventListener('click', loadHandoffs);
  document.getElementById('refreshSystemBtn')?.addEventListener('click', loadSystemHealth);
  document.getElementById('logoutBtn')?.addEventListener('click', () => handleLogout());
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Global bootstrap
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
  checkAuthSession();
});
