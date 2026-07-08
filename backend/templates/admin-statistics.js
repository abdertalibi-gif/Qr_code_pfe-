/* ── Admin Statistics Page ── */
async function initPage() {
  await loadStats();
  setupEventListeners();
}

async function loadStats() {
  try {
    const data = await API.apiFetch('/statistics/');
    renderOverallStats(data.overall || data);
    renderCharts(data);
  } catch (e) {
    document.getElementById('statsOverallContainer').innerHTML =
      '<div class="error-msg">Erreur: ' + esc(e.message) + '</div>';
  }
}

function renderOverallStats(stats) {
  const container = document.getElementById('statsOverallContainer');
  if (!stats) { container.innerHTML = '<p>Aucune statistique.</p>'; return; }
  const cards = [
    { label: 'Total étudiants', value: stats.total_students ?? '—' },
    { label: 'Total enseignants', value: stats.total_teachers ?? '—' },
    { label: 'Total classes', value: stats.total_classes ?? '—' },
    { label: 'Total séances', value: stats.total_sessions ?? '—' },
    { label: 'Présences', value: stats.total_present ?? '—', color: 'var(--green)' },
    { label: 'Absences', value: stats.total_absent ?? '—', color: 'var(--red)' },
    { label: 'Taux présence', value: stats.attendance_rate ? stats.attendance_rate + '%' : '—' },
    { label: 'Taux absence', value: stats.absence_rate ? stats.absence_rate + '%' : '—' },
  ];
  container.innerHTML = '<div class="stats-grid">' +
    cards.map(c => '<div class="stat-card" style="' + (c.color ? 'border-left:4px solid ' + c.color : '') + '">' +
      '<strong>' + esc(c.label) + '</strong>' +
      '<span class="stat-value">' + c.value + '</span>' +
    '</div>').join('') +
  '</div>';
}

function renderCharts(data) {
  if (typeof Chart === 'undefined') return;
  const ctxDaily = document.getElementById('chartDailyAttendance');
  if (ctxDaily && data.daily_attendance) {
    new Chart(ctxDaily, {
      type: 'line',
      data: {
        labels: data.daily_attendance.map(d => d.date),
        datasets: [
          { label: 'Présents', data: data.daily_attendance.map(d => d.present), borderColor: 'var(--green)', fill: false },
          { label: 'Absents', data: data.daily_attendance.map(d => d.absent), borderColor: 'var(--red)', fill: false },
        ],
      },
      options: { responsive: true, plugins: { legend: { position: 'top' } } },
    });
  }
  const ctxClasses = document.getElementById('chartByClass');
  if (ctxClasses && data.by_class) {
    new Chart(ctxClasses, {
      type: 'bar',
      data: {
        labels: data.by_class.map(c => c.name),
        datasets: [{
          label: 'Taux présence (%)',
          data: data.by_class.map(c => c.rate),
          backgroundColor: 'rgba(76, 175, 80, 0.6)',
        }],
      },
      options: { responsive: true, scales: { y: { min: 0, max: 100 } } },
    });
  }
}

function setupEventListeners() {
  document.getElementById('btnRefreshStats')?.addEventListener('click', loadStats);
}