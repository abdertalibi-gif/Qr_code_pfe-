/* ── Admin Sessions Page ── */
let allSessions = [];
let currentPage = 1;
const PAGE_SIZE = 10; // 10 séances par page

async function initPage() {
  await loadSessions();
  setupEventListeners();
}

/**
 * Tri déterministe décroissant :
 * 1. Date réelle décroissante
 * 2. Heure de début réelle décroissante
 * 3. Identifiant décroissant (critère stable pour départager les dates/heures identiques)
 */
function sortSessionsDesc(list) {
  return list.slice().sort((a, b) => {
    const dateA = a.date || '';
    const dateB = b.date || '';
    if (dateA !== dateB) return dateB.localeCompare(dateA);

    const timeA = a.start_time || '';
    const timeB = b.start_time || '';
    if (timeA !== timeB) return timeB.localeCompare(timeA);

    return (b.id || 0) - (a.id || 0);
  });
}

async function loadSessions() {
  const tbody = document.getElementById('sessionsBody');
  const countLabel = document.getElementById('sessionsCountLabel');
  if (tbody) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Chargement…</td></tr>';
  }
  if (countLabel) {
    countLabel.textContent = 'Chargement du nombre de séances…';
  }
  try {
    const data = await API.apiFetch('/sessions/');
    const rawList = Array.isArray(data) ? data : (data.results || []);
    // Application du tri déterministe (déjà trié côté API, sécurisé côté client)
    allSessions = sortSessionsDesc(rawList);
    currentPage = 1;
    renderSessions();
  } catch (e) {
    if (tbody) {
      tbody.innerHTML =
        '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
    }
    if (countLabel) {
      countLabel.textContent = 'Erreur de chargement.';
    }
  }
}

function getSessionTitle(s) {
  return s.title || s.subject || s.matiere_name || s.module_name || 'Séance';
}

function getSessionClass(s) {
  return s.class_name || s.classe_name || '—';
}

function getSessionMatiere(s) {
  return s.matiere_name || s.module_name || s.subject || '—';
}

function getSessionTeacher(s) {
  return s.teacher_name || '—';
}

function getSessionRoom(s) {
  if (s.room_name) {
    return s.block_name ? `${s.block_name} - ${s.room_name}` : s.room_name;
  }
  if (s.amphitheater_name) {
    return s.amphitheater_name;
  }
  if (s.block_name) {
    return `Bloc ${s.block_name}`;
  }
  return '—';
}

function getSessionStatus(s) {
  if (s.status) return s.status;
  if (s.is_closed) return 'completed';
  if (s.is_active) return 'active';
  return 'inactive';
}

function renderPaginationControls(containerId, current, totalPages, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = '<div style="display:flex;align-items:center;gap:.35rem;flex-wrap:wrap">';

  // Bouton « Précédent »
  const isFirst = current <= 1;
  html += `<button class="btn sm outline" id="${containerId}Prev" ${isFirst ? 'disabled style="opacity:.45;cursor:not-allowed"' : ''}>← Précédent</button>`;

  // Numéros de page
  for (let p = 1; p <= totalPages; p++) {
    const isActive = p === current;
    const style = isActive
      ? 'background:var(--primary,#0F7DB8);color:#fff;border-color:var(--primary,#0F7DB8);font-weight:700;box-shadow:0 1px 3px rgba(15,125,184,0.3);'
      : '';
    html += `<button class="btn sm outline ${isActive ? 'active' : ''}" style="${style}" data-page="${p}">${p}</button>`;
  }

  // Bouton « Suivant »
  const isLast = current >= totalPages;
  html += `<button class="btn sm outline" id="${containerId}Next" ${isLast ? 'disabled style="opacity:.45;cursor:not-allowed"' : ''}>Suivant →</button>`;

  html += `<span style="margin-left:.75rem;font-size:.85rem;color:var(--text-secondary,#6B7280)">Page ${current} sur ${totalPages}</span>`;
  html += '</div>';

  container.innerHTML = html;

  const prevBtn = document.getElementById(`${containerId}Prev`);
  if (prevBtn && !isFirst) {
    prevBtn.addEventListener('click', () => onPageChange(current - 1));
  }
  const nextBtn = document.getElementById(`${containerId}Next`);
  if (nextBtn && !isLast) {
    nextBtn.addEventListener('click', () => onPageChange(current + 1));
  }
  container.querySelectorAll('button[data-page]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const page = parseInt(e.currentTarget.getAttribute('data-page'), 10);
      if (page && page !== current) {
        onPageChange(page);
      }
    });
  });
}

function renderSessions() {
  const tbody = document.getElementById('sessionsBody');
  const countLabel = document.getElementById('sessionsCountLabel');
  if (!tbody) return;

  const q = searchQuery('searchSessions');
  const filtered = allSessions.filter(s => {
    const title = getSessionTitle(s);
    const cls = getSessionClass(s);
    const mat = getSessionMatiere(s);
    const teacher = getSessionTeacher(s);
    const room = getSessionRoom(s);
    const status = getSessionStatus(s);
    const type = s.session_type || s.type || '';
    return matchesQuery(q, title, cls, mat, teacher, room, status, type);
  });

  const total = allSessions.length;
  const filteredCount = filtered.length;

  if (!filteredCount) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">' + (q ? 'Aucun résultat.' : 'Aucune séance.') + '</td></tr>';
    if (countLabel) {
      countLabel.textContent = q ? `0 séance trouvée sur un total de ${total} séances` : `0 séance au total`;
    }
    const paginationEl = document.getElementById('sessionsPagination');
    if (paginationEl) paginationEl.innerHTML = '';
    return;
  }

  const totalPages = Math.ceil(filteredCount / PAGE_SIZE) || 1;
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  const startIdx = (currentPage - 1) * PAGE_SIZE;
  const pageItems = filtered.slice(startIdx, startIdx + PAGE_SIZE);

  if (countLabel) {
    const from = startIdx + 1;
    const to = Math.min(startIdx + PAGE_SIZE, filteredCount);
    if (q) {
      countLabel.textContent = `Affichage de ${from} à ${to} sur ${filteredCount} résultat(s) trouvé(s) (Total général : ${total} séances)`;
    } else {
      countLabel.textContent = `Affichage des séances ${from} à ${to} sur ${total} au total (Page ${currentPage} sur ${totalPages})`;
    }
  }

  tbody.innerHTML = pageItems.map((s, idx) => {
    const title = getSessionTitle(s);
    const cls = getSessionClass(s);
    const mat = getSessionMatiere(s);
    const teacher = getSessionTeacher(s);
    const room = getSessionRoom(s);
    const status = getSessionStatus(s);
    const statusClass = status === 'active' ? 'badge-success' : status === 'completed' ? 'badge-info' : 'badge-warning';

    return '<tr>' +
      '<td><span style="color:var(--muted)">' + (startIdx + idx + 1) + '</span></td>' +
      '<td><strong>' + esc(title) + '</strong></td>' +
      '<td>' + esc(cls) + '</td>' +
      '<td>' + esc(mat) + '</td>' +
      '<td>' + esc(teacher) + '</td>' +
      '<td>' + esc(room) + '</td>' +
      '<td><span class="badge ' + statusClass + '">' + esc(status) + '</span></td>' +
    '</tr>';
  }).join('');

  renderPaginationControls('sessionsPagination', currentPage, totalPages, (newPage) => {
    currentPage = newPage;
    renderSessions();
  });
}

function setupEventListeners() {
  bindSearchInput('searchSessions', () => {
    currentPage = 1;
    renderSessions();
  });

  document.getElementById('btnRefreshSessions')?.addEventListener('click', loadSessions);

  document.getElementById('btnOpenCreateSession')?.addEventListener('click', () => {
    if (window.SessionForm) {
      SessionForm.init({
        isAdmin: true,
        userRole: 'admin',
        onSaved: () => loadSessions(),
      });
      SessionForm.open();
    }
  });

  document.getElementById('btnExportWizard')?.addEventListener('click', () => {
    openModal('modalExportWizard');
  });
}