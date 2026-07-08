/**
 * admin-common.js — Shared utilities for all admin pages
 * Loaded via <script src="/admin-common.js"></script> on every admin page.
 */

const API_BASE = '/api/v1';

/* ─── Token helpers ─────────────────────────────────────────────────────── */

function getToken() {
  return localStorage.getItem('access_token');
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

function setTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  if (refresh !== undefined) {
    localStorage.setItem('refresh_token', refresh);
  }
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('current_user');
}

/* ─── Token refresh ─────────────────────────────────────────────────────── */

let _refreshPromise = null;

async function refreshAccessToken() {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) throw new Error('No refresh token');

    const res = await fetch(`${API_BASE}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });

    if (!res.ok) throw new Error('Refresh failed');

    const data = await res.json();
    setTokens(data.access);
    return data.access;
  })();

  _refreshPromise.finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

/* ─── Core fetch wrapper ────────────────────────────────────────────────── */

const FETCH_TIMEOUT = 30000;

async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || FETCH_TIMEOUT);

  const makeRequest = async (token) => {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    if (options.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    return fetch(url, { ...options, headers, signal: controller.signal });
  };

  try {
    let token = getToken();
    let res;
    try {
      res = await makeRequest(token);
    } catch (fetchErr) {
      if (fetchErr.name === 'AbortError') {
        throw new Error(
          'La requête a pris trop de temps. ' +
          `Vérifiez que le serveur est bien démarré et réessayez. (timeout: ${options.timeout || FETCH_TIMEOUT}ms)`
        );
      }
      throw fetchErr;
    }

    if (res.status === 401) {
      try {
        token = await refreshAccessToken();
        res = await makeRequest(token);
      } catch {
        clearTokens();
        window.location.href = '/login/';
        throw new Error('Unauthenticated');
      }
    }

    if (!res.ok) {
      let errMsg = `HTTP ${res.status}`;
      try {
        const errData = await res.json();
        if (typeof errData === 'string') {
          errMsg = errData;
        } else if (errData.detail) {
          errMsg = errData.detail;
        } else if (errData.non_field_errors) {
          errMsg = Array.isArray(errData.non_field_errors)
            ? errData.non_field_errors.join(' ')
            : String(errData.non_field_errors);
        } else if (typeof errData === 'object') {
          const parts = [];
          for (const [key, value] of Object.entries(errData)) {
            if (Array.isArray(value)) parts.push(`${key}: ${value.join(', ')}`);
            else parts.push(`${key}: ${value}`);
          }
          errMsg = parts.join(' | ') || JSON.stringify(errData);
        }
      } catch {}
      throw new Error(errMsg);
    }

    if (res.status === 204) return null;

    const contentType = res.headers.get('Content-Type') || '';
    if (contentType.includes('application/json')) {
      return res.json();
    }
    return res.blob();
  } finally {
    clearTimeout(timeoutId);
  }
}

async function downloadFile(path, filename) {
  const blob = await apiFetch(path);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function uploadFile(path, formData) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ─── Auth helpers ──────────────────────────────────────────────────────── */

async function requireAuth(allowedRoles = []) {
  const token = getToken();
  if (!token) throw new Error('Not authenticated');

  const cached = localStorage.getItem('current_user');
  if (cached) {
    const user = JSON.parse(cached);
    if (!allowedRoles.length || allowedRoles.includes(user.role)) {
      return user;
    }
  }

  const res = await apiFetch('/auth/me/');
  localStorage.setItem('current_user', JSON.stringify(res));
  if (allowedRoles.length && !allowedRoles.includes(res.role)) {
    throw new Error('Forbidden');
  }
  return res;
}

function logout() {
  clearTokens();
  window.location.href = '/login/';
}

/* ─── Utility functions ─────────────────────────────────────────────────── */

function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&#039;');
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('fr-FR');
}

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function searchQuery(id) {
  return (document.getElementById(id)?.value || '').trim().toLowerCase();
}

function matchesQuery(query, ...values) {
  if (!query) return true;
  return values.some(v => String(v ?? '').toLowerCase().includes(query));
}

function bindSearchInput(id, renderFn) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('input', renderFn);
}

function showSpinner(id, show) {
  const el = document.getElementById(id);
  if (el) el.style.display = show ? 'inline-block' : 'none';
}

/* ─── Toast ─────────────────────────────────────────────────────────────── */

let _toastTimer;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.className = type;
  t.innerHTML = `<span>${type === 'success' ? '✅' : '❌'}</span><span>${msg}</span>`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { t.className = ''; }, 3500);
}

/* ─── Modal helpers ─────────────────────────────────────────────────────── */

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
}

function setupModalCloseHandlers() {
  document.querySelectorAll('[data-close]').forEach(el => {
    el.addEventListener('click', () => closeModal(el.dataset.close));
  });
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal(backdrop.id);
    });
  });
}

/* ─── Pagination helpers ────────────────────────────────────────────────── */

function createPaginationControls(containerId, currentPage, totalPages, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (totalPages <= 1) {
    container.classList.add('hidden');
    return;
  }
  container.classList.remove('hidden');
  container.innerHTML = `
    <button class="btn sm outline" id="${containerId}Prev" ${currentPage <= 1 ? 'disabled' : ''}>← Précédent</button>
    <span id="${containerId}Info">Page ${currentPage} / ${totalPages}</span>
    <button class="btn sm outline" id="${containerId}Next" ${currentPage >= totalPages ? 'disabled' : ''}>Suivant →</button>
  `;
  document.getElementById(`${containerId}Prev`).addEventListener('click', () => {
    if (currentPage > 1) onPageChange(currentPage - 1);
  });
  document.getElementById(`${containerId}Next`).addEventListener('click', () => {
    if (currentPage < totalPages) onPageChange(currentPage + 1);
  });
}

/* ─── Table rendering helpers ───────────────────────────────────────────── */

function renderTable(tbodyId, items, renderRow, emptyMessage = 'Aucun élément.') {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="99">${emptyMessage}</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map((item, i) => renderRow(item, i + 1)).join('');
}

/* ─── Export shared objects ─────────────────────────────────────────────── */

window.API = {
  apiFetch,
  downloadFile,
  uploadFile,
  requireAuth,
  logout,
  esc,
  formatDate,
  formatDateTime,
  getToken,
  setTokens,
  clearTokens,
};

window.AdminUtils = {
  esc,
  formatDate,
  formatDateTime,
  searchQuery,
  matchesQuery,
  bindSearchInput,
  showSpinner,
  showToast,
  openModal,
  closeModal,
  setupModalCloseHandlers,
  createPaginationControls,
  renderTable,
};