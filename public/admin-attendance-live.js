/* ── Admin Attendance Live Page ── */
let allAttendance = [];
let allSessions = [];
let allClasses = [];
let adminLiveWS = null;

async function initPage() {
  await Promise.all([loadClasses(), loadSessions()]);
  await loadAttendance();
  connectAdminLiveWS();
}

async function loadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    allClasses = Array.isArray(data) ? data : (data.results || []);
    populateAttendanceFilters();
  } catch (e) {
    showToast('Erreur chargement classes: ' + e.message, 'error');
  }
}

async function loadSessions() {
  try {
    const data = await API.apiFetch('/sessions/');
    allSessions = Array.isArray(data) ? data : (data.results || []);
  } catch (e) {
    showToast('Erreur chargement séances: ' + e.message, 'error');
  }
}

async function loadAttendance() {
  const classeId = document.getElementById('filterClasse')?.value || '';
  const sessionId = document.getElementById('filterSession')?.value || '';
  let path = '/attendance/';
  const params = new URLSearchParams();
  if (classeId) params.set('classe', classeId);
  if (sessionId) params.set('session', sessionId);
  if (params.toString()) path += '?' + params;

  try {
    const data = await API.apiFetch(path);
    allAttendance = Array.isArray(data) ? data : (data.results || []);
    renderAttendanceTable();
    updateAttendanceStats();
  } catch (e) {
    document.getElementById('attendanceBody').innerHTML =
      '<tr class="empty-row"><td colspan="9">Échec du chargement: ' + esc(e.message) + '</td></tr>';
  }
}

function populateAttendanceFilters() {
  const classeSel = document.getElementById('filterClasse');
  const sessionSel = document.getElementById('filterSession');
  if (!classeSel || !sessionSel) return;

  const classeVal = classeSel.value;
  classeSel.innerHTML = '<option value="">Toutes les classes</option>';
  allClasses.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = (c.filiere_name || '—') + ' — ' + (c.semestre_name || '');
    classeSel.appendChild(opt);
  });
  classeSel.value = classeVal;

  const sessionVal = sessionSel.value;
  sessionSel.innerHTML = '<option value="">Toutes les séances</option>';
  const filtered = classeVal
    ? allSessions.filter(s => String(s.classe) === String(classeVal))
    : allSessions;
  filtered.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = (s.subject || '') + ' · ' + API.formatDate(s.date);
    sessionSel.appendChild(opt);
  });
  sessionSel.value = sessionVal;
}

function updateAttendanceStats() {
  const today = new Date().toDateString();
  const todayCount = allAttendance.filter(r => {
    const d = new Date(r.validation_time);
    return !Number.isNaN(d.getTime()) && d.toDateString() === today;
  }).length;
  const subjectSet = new Set(allAttendance.map(r => r.subject).filter(Boolean));
  document.getElementById('statTotal').textContent = allAttendance.length;
  document.getElementById('statToday').textContent = todayCount;
  document.getElementById('statActiveCourses').textContent = subjectSet.size;
}

function getFilteredAttendance() {
  const query = searchQuery('searchAttendance');
  if (!query) return allAttendance;
  return allAttendance.filter(r => matchesQuery(
    query,
    r.student_name, r.student_code_massar, r.subject,
    r.classe_session, r.classe_name, r.teacher_name,
    API.formatDate(r.session_date), API.formatDateTime(r.validation_time)
  ));
}

function renderAttendanceTable() {
  const tbody = document.getElementById('attendanceBody');
  const filtered = getFilteredAttendance();
  const query = searchQuery('searchAttendance');
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="9">' + (query ? 'Aucun résultat.' : 'Aucune présence enregistrée.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((r, i) => attendanceRowHtml(r, i + 1)).join('');
}

function attendanceRowHtml(r, idx, isNew) {
  return '<tr class="' + (isNew ? 'new-row' : '') + '">' +
    '<td style="color:var(--muted)">' + idx + '</td>' +
    '<td><strong>' + esc(r.student_name) + '</strong></td>' +
    '<td style="font-family:monospace;color:var(--accent)">' + esc(r.student_code_massar) + '</td>' +
    '<td>' + esc(r.subject || '—') + '</td>' +
    '<td style="color:var(--muted)">' + esc(r.classe_session || r.classe_name || '—') + '</td>' +
    '<td style="color:var(--muted)">' + esc(r.teacher_name || '—') + '</td>' +
    '<td style="color:var(--muted)">' + API.formatDate(r.session_date) + '</td>' +
    '<td style="color:var(--muted);font-size:.8rem">' + API.formatDateTime(r.validation_time) + '</td>' +
    '<td><span class="badge badge-present">Présent</span></td>' +
  '</tr>';
}

function prependAttendanceRecord(record) {
  if (allAttendance.some(r => r.id === record.id)) return;
  allAttendance.unshift(record);
  updateAttendanceStats();
  renderAttendanceTable();
  showToast(t('markedPresent', { name: record.student_name, course: record.subject || '' }), 'success');
}

function connectAdminLiveWS() {
  if (adminLiveWS) adminLiveWS.close();
  adminLiveWS = API.connectAttendanceWs(
    '/ws/attendance/live/admin/',
    prependAttendanceRecord,
    (status) => {
      const dot = document.getElementById('adminWsDot');
      const text = document.getElementById('adminWsStatus');
      if (status === 'connected') {
        dot.className = 'ws-dot connected';
        text.textContent = t('live');
      } else if (status === 'error') {
        dot.className = 'ws-dot error';
        text.textContent = t('connectionError');
      } else {
        dot.className = 'ws-dot';
        text.textContent = t('disconnected');
      }
    },
  );
}

/* ── Event listeners ── */
document.getElementById('filterClasse')?.addEventListener('change', () => {
  populateAttendanceFilters();
  loadAttendance();
});
document.getElementById('filterSession')?.addEventListener('change', loadAttendance);
bindSearchInput('searchAttendance', renderAttendanceTable);