/**
 * admin-common.js — Shared admin UI utilities
 * Loaded after api.js on every admin page.
 */

/* ─── Utility functions ─────────────────────────────────────────────────── */

function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
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