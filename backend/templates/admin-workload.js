/* ── Admin Workload Dashboard ── */
let wlChartHours = null;
let wlChartPie = null;

function esc(str) { return (str == null ? '' : String(str)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

async function initPage() {
  await Promise.all([loadDepartments(), loadFilieres(), loadAcademicYears()]);
  populatePeriodYears();
  wlLoadData();
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    const list = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('wlDepartment');
    sel.innerHTML = '<option value="">Tous</option>';
    list.forEach(function (d) { sel.innerHTML += '<option value="' + d.id + '">' + esc(d.name) + '</option>'; });
  } catch (e) { /* ignore */ }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    const list = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('wlFiliere');
    sel.innerHTML = '<option value="">Toutes</option>';
    list.forEach(function (f) { sel.innerHTML += '<option value="' + f.id + '">' + esc(f.name) + '</option>'; });
  } catch (e) { /* ignore */ }
}

async function loadAcademicYears() {
  var sel = document.getElementById('wlAcYear');
  var cur = new Date().getFullYear();
  var html = '<option value="">Toutes</option>';
  for (var y = cur + 1; y >= cur - 5; y--) html += '<option value="' + y + '">' + y + '</option>';
  sel.innerHTML = html;
}

function populatePeriodYears() {
  var sel = document.getElementById('wlYear');
  var cur = new Date().getFullYear();
  var html = '<option value="">—</option>';
  for (var y = cur; y >= cur - 5; y--) html += '<option value="' + y + '">' + y + '</option>';
  sel.innerHTML = html;
}

function wlOnPeriodModeChange() {
  var mode = document.getElementById('wlPeriodMode').value;
  document.getElementById('wlMonthGroup').style.display = mode === 'month' ? '' : 'none';
  document.getElementById('wlYearGroup').style.display = mode === 'month' ? '' : 'none';
  document.getElementById('wlDateStartGroup').style.display = mode === 'range' ? '' : 'none';
  document.getElementById('wlDateEndGroup').style.display = mode === 'range' ? '' : 'none';
  wlLoadData();
}

function wlResetFilters() {
  ['wlAcYear','wlDepartment','wlFiliere','wlMonth','wlYear','wlDateStart','wlDateEnd'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('wlPeriodMode').value = 'all';
  document.getElementById('wlMonthGroup').style.display = 'none';
  document.getElementById('wlYearGroup').style.display = 'none';
  document.getElementById('wlDateStartGroup').style.display = 'none';
  document.getElementById('wlDateEndGroup').style.display = 'none';
  wlLoadData();
}

/* ── Build query string ── */
function wlBuildQuery() {
  var params = new URLSearchParams();
  var ac = document.getElementById('wlAcYear').value;
  var dept = document.getElementById('wlDepartment').value;
  var fil = document.getElementById('wlFiliere').value;
  if (ac) params.set('year', ac);
  if (dept) params.set('department_id', dept);
  if (fil) params.set('filiere_id', fil);
  var mode = document.getElementById('wlPeriodMode').value;
  if (mode === 'month') {
    var m = document.getElementById('wlMonth').value;
    var y = document.getElementById('wlYear').value;
    if (m) params.set('month', m);
    if (y) params.set('year', y);
  } else if (mode === 'range') {
    var ds = document.getElementById('wlDateStart').value;
    var de = document.getElementById('wlDateEnd').value;
    if (ds) params.set('start_date', ds);
    if (de) params.set('end_date', de);
  }
  return params.toString();
}

/* ── Load & render ── */
async function wlLoadData() {
  var tbody = document.getElementById('wlBody');
  tbody.innerHTML = '<tr class="empty-row"><td colspan="12">Chargement...</td></tr>';
  try {
    var qs = wlBuildQuery();
    var url = '/api/v1/teacher-workload/' + (qs ? '?' + qs : '');
    var data = await API.apiFetch(url);
    var teachers = Array.isArray(data) ? data : (data.teachers || []);
    var totals = data.totals || null;
    wlRenderStats(totals);
    wlRenderTable(tbody, teachers, totals);
    wlRenderCharts(teachers);
  } catch (e) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="12">Erreur : ' + esc(e.message) + '</td></tr>';
  }
}

function wlRenderStats(totals) {
  var row = document.getElementById('wlStatsRow');
  if (!totals) { row.innerHTML = ''; return; }
  row.innerHTML =
    '<div class="stat-card" style="background:var(--surface-2);padding:.85rem;border-radius:10px;text-align:center">' +
      '<div style="font-size:1.5rem;font-weight:700">' + totals.cm_hours + '</div>' +
      '<div style="font-size:.78rem;color:var(--muted)">Heures CM</div>' +
    '</div>' +
    '<div class="stat-card" style="background:var(--surface-2);padding:.85rem;border-radius:10px;text-align:center">' +
      '<div style="font-size:1.5rem;font-weight:700">' + totals.td_hours + '</div>' +
      '<div style="font-size:.78rem;color:var(--muted)">Heures TD</div>' +
    '</div>' +
    '<div class="stat-card" style="background:var(--surface-2);padding:.85rem;border-radius:10px;text-align:center">' +
      '<div style="font-size:1.5rem;font-weight:700">' + totals.tp_hours + '</div>' +
      '<div style="font-size:.78rem;color:var(--muted)">Heures TP</div>' +
    '</div>' +
    '<div class="stat-card" style="background:var(--accent);padding:.85rem;border-radius:10px;text-align:center;color:#fff">' +
      '<div style="font-size:1.5rem;font-weight:700">' + totals.equivalent_hours + '</div>' +
      '<div style="font-size:.78rem;opacity:.85">Charge équivalente totale</div>' +
    '</div>' +
    '<div class="stat-card" style="background:var(--surface-2);padding:.85rem;border-radius:10px;text-align:center">' +
      '<div style="font-size:1.5rem;font-weight:700">' + totals.total_sessions + '</div>' +
      '<div style="font-size:.78rem;color:var(--muted)">Total séances</div>' +
    '</div>';
}

function wlRenderTable(tbody, teachers, totals) {
  if (!teachers.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="12">Aucune donnée pour les filtres sélectionnés.</td></tr>';
    return;
  }
  var html = '';
  teachers.forEach(function (t, i) {
    var rankClass = i === 0 ? ' style="color:var(--accent);font-weight:700"' : '';
    html += '<tr>' +
      '<td' + rankClass + '>' + (i + 1) + '</td>' +
      '<td><strong>' + esc(t.last_name) + ' ' + esc(t.first_name) + '</strong></td>' +
      '<td>' + esc(t.department || '—') + '</td>' +
      '<td>' + esc(t.filiere || '—') + '</td>' +
      '<td>' + t.cm_count + '</td>' +
      '<td>' + t.td_count + '</td>' +
      '<td>' + t.tp_count + '</td>' +
      '<td>' + t.cm_hours + '</td>' +
      '<td>' + t.td_hours + '</td>' +
      '<td>' + t.tp_hours + '</td>' +
      '<td>' + t.total_sessions + '</td>' +
      '<td style="font-weight:700;color:var(--primary)">' + t.equivalent_hours + '</td>' +
    '</tr>';
  });
  // Totals row
  if (totals) {
    html += '<tr style="font-weight:700;background:var(--surface-2)">' +
      '<td colspan="2">TOTAL GÉNÉRAL</td>' +
      '<td></td><td></td>' +
      '<td>' + totals.cm_count + '</td>' +
      '<td>' + totals.td_count + '</td>' +
      '<td>' + totals.tp_count + '</td>' +
      '<td>' + totals.cm_hours + '</td>' +
      '<td>' + totals.td_hours + '</td>' +
      '<td>' + totals.tp_hours + '</td>' +
      '<td>' + totals.total_sessions + '</td>' +
      '<td style="color:var(--accent)">' + totals.equivalent_hours + '</td>' +
    '</tr>';
  }
  tbody.innerHTML = html;
}

function wlRenderCharts(teachers) {
  if (!teachers.length) {
    if (wlChartHours) { wlChartHours.destroy(); wlChartHours = null; }
    if (wlChartPie) { wlChartPie.destroy(); wlChartPie = null; }
    return;
  }
  var labels = teachers.map(function (t) { return t.last_name + ' ' + t.first_name; });
  var cmData = teachers.map(function (t) { return t.cm_hours; });
  var tdData = teachers.map(function (t) { return t.td_hours; });
  var tpData = teachers.map(function (t) { return t.tp_hours; });
  var eqData = teachers.map(function (t) { return t.equivalent_hours; });

  var barCtx = document.getElementById('wlChartHours');
  if (wlChartHours) wlChartHours.destroy();
  wlChartHours = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'CM', data: cmData, backgroundColor: '#0F7DB8', borderRadius: 4 },
        { label: 'TD', data: tdData, backgroundColor: '#F28C28', borderRadius: 4 },
        { label: 'TP', data: tpData, backgroundColor: '#10b981', borderRadius: 4 },
        { label: 'Équivalent', data: eqData, backgroundColor: 'rgba(15,125,184,0.15)', borderColor: '#0F7DB8', borderWidth: 2, type: 'line', tension: 0.3, pointRadius: 4, pointBackgroundColor: '#0F7DB8' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { x: { ticks: { maxRotation: 45, font: { size: 10 } } }, y: { beginAtZero: true, title: { display: true, text: 'Heures' } } },
      plugins: { legend: { position: 'top', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } } },
    },
  });

  // Pie chart: repartition CM/TD/TP
  var totalCM = cmData.reduce(function (a, b) { return a + b; }, 0);
  var totalTD = tdData.reduce(function (a, b) { return a + b; }, 0);
  var totalTP = tpData.reduce(function (a, b) { return a + b; }, 0);
  var pieCtx = document.getElementById('wlChartPie');
  if (wlChartPie) wlChartPie.destroy();
  wlChartPie = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: ['CM (' + totalCM.toFixed(1) + 'h)', 'TD (' + totalTD.toFixed(1) + 'h)', 'TP (' + totalTP.toFixed(1) + 'h)'],
      datasets: [{
        data: [totalCM, totalTD, totalTP],
        backgroundColor: ['#0F7DB8', '#F28C28', '#10b981'],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } } },
    },
  });
}

if (typeof initPage === 'function') window.initPage = initPage;
