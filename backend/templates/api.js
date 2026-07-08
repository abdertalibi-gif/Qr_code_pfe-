/**
 * api.js — Shared API utility for QR Attendance System
 * Loaded via <script src="/api.js"></script> on every page.
 * Exposes a global `window.API` object.
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

const FETCH_TIMEOUT = 30000; // 30s

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
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function uploadFile(path, formData) {
  return apiFetch(path, { method: 'POST', body: formData });
}

/* ─── Auth helpers ──────────────────────────────────────────────────────── */

async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    let msg = 'Login failed';
    try {
      const d = await res.json();
      msg = d.detail || d.message || msg;
    } catch {}
    throw new Error(msg);
  }

  const data = await res.json();
  setTokens(data.access, data.refresh);
  localStorage.setItem('current_user', JSON.stringify(data.user));
  return data;
}

async function getMe() {
  const cached = localStorage.getItem('current_user');
  if (cached) {
    try { return JSON.parse(cached); } catch {}
  }
  const user = await apiFetch('/auth/me/');
  localStorage.setItem('current_user', JSON.stringify(user));
  return user;
}

function logout() {
  clearTokens();
  window.location.href = '/login/';
}

/* ─── Auth guard ────────────────────────────────────────────────────────── */

/**
 * Call at the top of any protected page.
 * @param {string|string[]} [allowedRoles] — if provided, redirect if role not in list
 * @returns {Promise<object>} the current user object
 */
async function requireAuth(allowedRoles) {
  if (!getToken()) {
    window.location.href = '/login/';
    throw new Error('No token');
  }
  try {
    const user = await getMe();
    if (allowedRoles) {
      const roles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];
      if (!roles.includes(user.role)) {
        window.location.href = '/login/';
        throw new Error('Forbidden');
      }
    }
    return user;
  } catch (e) {
    if (e.message === 'Forbidden') throw e;
    window.location.href = '/login/';
    throw e;
  }
}

/* ─── WebSocket helpers ─────────────────────────────────────────────────── */

function getWsBase() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}`;
}

function connectAttendanceWs(path, onMessage, onStatus) {
  const ws = new WebSocket(`${getWsBase()}${path}`);

  ws.onopen = () => onStatus?.('connected');
  ws.onerror = () => onStatus?.('error');
  ws.onclose = () => onStatus?.('disconnected');
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const record = data.data || data;
      if (record && record.id) onMessage(record);
    } catch {}
  };

  return ws;
}

function formatDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ─── Expose global window.API ──────────────────────────────────────────── */

window.API = {
  BASE: API_BASE,
  getToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  apiFetch,
  login,
  getMe,
  logout,
  requireAuth,
  getWsBase,
  connectAttendanceWs,
  formatDateTime,
  formatDate,
  esc,
  downloadFile,
  uploadFile,
};
