/* ── Admin Reports Page ── */
let reportData = null;

async function initPage() {
  setupEventListeners();
  await runReport();
}

async function runReport() {
  const type = document.getElementById('reportType')?.value || 'attendance';
  const from = document.getElementById('reportDateFrom')?.value || '';
  const to = document.getElementById('reportDateTo')?.value || '';
  const classId = document.getElementById('reportClass')?.value || '';
  const deptId = document.getElementById('reportDept')?.value || '';
  const format = document.getElementById('reportFormat')?.value || 'html';

  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  if (classId) params.set('class_id', classId);
  if (deptId) params.set('department_id', deptId);

  showToast('Génération du rapport...', 'info');

  try {
    if (format === 'html') {
      const data = await API.apiFetch('/reports/?' + params.toString());
      reportData = data;
      renderReport(data, type);
    } else if (format === 'csv') {
      const blob = await API.apiFetch('/reports/export/?' + params.toString() + '&format=csv', {}, true);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = type + '_report.csv'; a.click();
      window.URL.revokeObjectURL(url);
      showToast('CSV téléchargé.', 'success');
    } else if (format === 'pdf') {
      const blob = await API.apiFetch('/reports/export/?' + params.toString() + '&format=pdf', {}, true);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = type + '_report.pdf'; a.click();
      window.URL.revokeObjectURL(url);
      showToast('PDF téléchargé.', 'success');
    }
  } catch (e) {
    document.getElementById('reportContent').innerHTML =
      '<div class="error-msg">Erreur: ' + esc(e.message) + '</div>';
    showToast('Erreur de génération: ' + e.message, 'error');
  }
}

function renderReport(data, type) {
  const container = document.getElementById('reportContent');
  if (!data) {
    container.innerHTML = '<p>Aucune donnée.</p>';
    return;
  }
  let html = '<div class="report-summary">';
  html += '<h3>Rapport: ' + esc(type) + '</h3>';
  if (data.summary) {
    html += '<div class="summary-cards">';
    Object.entries(data.summary).forEach(([k, v]) => {
      html += '<div class="stat-card"><strong>' + esc(k) + '</strong><span>' + esc(String(v)) + '</span></div>';
    });
    html += '</div>';
  }
  html += '</div>';
  if (data.rows && data.rows.length) {
    html += '<table class="data-table"><thead><tr>';
    if (data.headers) data.headers.forEach(h => { html += '<th>' + esc(h) + '</th>'; });
    html += '</tr></thead><tbody>';
    data.rows.forEach(row => {
      html += '<tr>';
      row.forEach(cell => { html += '<td>' + esc(String(cell)) + '</td>'; });
      html += '</tr>';
    });
    html += '</tbody></table>';
  } else {
    html += '<p>Aucune ligne de données.</p>';
  }
  container.innerHTML = html;
}

async function loadReportFilters() {
  try {
    const classes = await API.apiFetch('/classes/');
    const cls = Array.isArray(classes) ? classes : (classes.results || []);
    const sel = document.getElementById('reportClass');
    if (sel) {
      sel.innerHTML = '<option value="">Toutes les classes</option>' +
        cls.map(c => '<option value="' + c.id + '">' + esc(c.name) + '</option>').join('');
    }
  } catch (e) { }
  try {
    const depts = await API.apiFetch('/departments/');
    const dd = Array.isArray(depts) ? depts : (depts.results || []);
    const sel = document.getElementById('reportDept');
    if (sel) {
      sel.innerHTML = '<option value="">Tous les départements</option>' +
        dd.map(d => '<option value="' + d.id + '">' + esc(d.name) + '</option>').join('');
    }
  } catch (e) { }
}

function setupEventListeners() {
  document.getElementById('btnGenerateReport')?.addEventListener('click', runReport);
  loadReportFilters();
  const today = new Date().toISOString().split('T')[0];
  const firstDay = new Date(Date.now() - 30*86400000).toISOString().split('T')[0];
  const fromInput = document.getElementById('reportDateFrom');
  const toInput = document.getElementById('reportDateTo');
  if (fromInput) fromInput.value = firstDay;
  if (toInput) toInput.value = today;
}