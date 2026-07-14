/* ── Teacher Workload Dashboard ── */

var wld = {
  data: null,
  teachers: [],
  filtered: [],
  sortKey: 'equivalent',
  sortDir: -1,
  barChart: null,
  pieChart: null,

  async init() {
    await Promise.all([
      this._loadDepts(),
      this._loadFilieres(),
      this._loadAcademicYears(),
    ]);
    this._initPeriod();
    await this.loadData();
  },

  /* ── Filter helpers ── */

  async _loadDepts() {
    try {
      var data = await API.apiFetch('/departments/');
      var depts = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldDept');
      depts.forEach(function (d) {
        var o = document.createElement('option');
        o.value = d.id;
        o.textContent = d.name;
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadFilieres() {
    try {
      var data = await API.apiFetch('/curriculum/filieres/');
      var fils = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldFiliere');
      fils.forEach(function (f) {
        var o = document.createElement('option');
        o.value = f.id;
        o.textContent = f.name;
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadAcademicYears() {
    try {
      var data = await API.apiFetch('/classes/');
      var classes = Array.isArray(data) ? data : (data.results || []);
      var years = new Set();
      classes.forEach(function (c) { if (c.academic_year) years.add(c.academic_year); });
      var sorted = Array.from(years).sort();
      var sel = document.getElementById('wldYear');
      sorted.forEach(function (y) {
        var o = document.createElement('option');
        o.value = y;
        o.textContent = y;
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  _initPeriod() {
    var now = new Date();
    document.getElementById('wldMonth').value = String(now.getMonth() + 1);
    document.getElementById('wldDateStart').value = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    document.getElementById('wldDateEnd').value = now.toISOString().split('T')[0];
  },

  onPeriodChange() {
    var val = document.getElementById('wldPeriod').value;
    document.getElementById('wldMonthGroup').style.display = val === 'month' ? 'block' : 'none';
    document.getElementById('wldDateStartGroup').style.display = val === 'range' ? 'block' : 'none';
    document.getElementById('wldDateEndGroup').style.display = val === 'range' ? 'block' : 'none';
    this.onFilterChange();
  },

  onFilterChange() {
    this._applyFilters();
    this._renderTable();
    this._renderCharts();
    this._updateStats();
  },

  _buildParams() {
    var params = {};
    var dept = document.getElementById('wldDept').value;
    var filiere = document.getElementById('wldFiliere').value;
    var year = document.getElementById('wldYear').value;
    var period = document.getElementById('wldPeriod').value;

    if (dept) params.department_id = dept;
    if (filiere) params.filiere_id = filiere;
    if (year) params.academic_year = year;

    if (period === 'month') {
      var m = document.getElementById('wldMonth').value;
      var y = document.getElementById('wldYear').value || new Date().getFullYear();
      if (m) { params.month = m; params.year = String(y); }
    } else if (period === 'range') {
      var ds = document.getElementById('wldDateStart').value;
      var de = document.getElementById('wldDateEnd').value;
      if (ds) params.start_date = ds;
      if (de) params.end_date = de;
    }
    return params;
  },

  async loadData() {
    try {
      var params = this._buildParams();
      var qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      var url = '/api/v1/teacher-workload-dashboard/' + (qs ? '?' + qs : '');
      var resp = await API.apiFetch(url);
      this.teachers = resp.teachers || [];
      this.totals = resp.totals || {};
      this.chartData = resp.chart_data || {};
      this.filtered = this.teachers.slice();
      this._renderTable();
      this._renderCharts();
      this._updateStats();
    } catch (e) {
      document.getElementById('wldBody').innerHTML = '<tr class="empty-row"><td colspan="9">Erreur: ' + API.esc(e.message) + '</td></tr>';
    }
  },

  /* ── Table ── */

  _applyFilters() {
    var dept = document.getElementById('wldDept').value;
    var filiere = document.getElementById('wldFiliere').value;
    var year = document.getElementById('wldYear').value;
    var period = document.getElementById('wldPeriod').value;

    this.filtered = this.teachers.filter(function (t) {
      if (dept && t.department && !t.department.toLowerCase().includes(dept)) return false;
      if (filiere && t.filieres && !t.filieres.toLowerCase().includes(filiere)) return false;
      return true;
    });

    this._sort();
  },

  _sort() {
    var key = this.sortKey;
    var dir = this.sortDir;
    this.filtered.sort(function (a, b) {
      var va, vb;
      if (key === 'name') { va = (a.last_name + a.first_name).toLowerCase(); vb = (b.last_name + b.first_name).toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'department') { va = (a.department || '').toLowerCase(); vb = (b.department || '').toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'filieres') { va = (a.filieres || '').toLowerCase(); vb = (b.filieres || '').toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'rank') return dir * (a.rank || a.id - b.id);
      if (key === 'cm') return dir * (a.cm_hours - b.cm_hours);
      if (key === 'td') return dir * (a.td_hours - b.td_hours);
      if (key === 'tp') return dir * (a.tp_hours - b.tp_hours);
      if (key === 'sessions') return dir * (a.total_sessions - b.total_sessions);
      return dir * (a.equivalent_hours - b.equivalent_hours);
    });
  },

  setSort(key) {
    if (this.sortKey === key) {
      this.sortDir *= -1;
    } else {
      this.sortKey = key;
      this.sortDir = -1;
    }
    this._sort();
    this._renderTable();
  },

  _renderTable() {
    var tbody = document.getElementById('wldBody');
    if (!this.filtered.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="9">Aucune donnée pour les filtres sélectionnés.</td></tr>';
      return;
    }
    tbody.innerHTML = this.filtered.map(function (t, i) {
      return '<tr>' +
        '<td style="color:var(--muted)">' + (i + 1) + '</td>' +
        '<td><strong>' + API.esc(t.first_name) + ' ' + API.esc(t.last_name) + '</strong></td>' +
        '<td>' + API.esc(t.department || '—') + '</td>' +
        '<td>' + API.esc(t.filieres || '—') + '</td>' +
        '<td style="text-align:right">' + t.cm_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.td_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.tp_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.total_sessions + '</td>' +
        '<td style="text-align:right;font-weight:700;color:var(--accent)">' + t.equivalent_hours.toFixed(2) + '</td>' +
      '</tr>';
    }).join('');

    // Update sort indicators
    document.querySelectorAll('.sortable').forEach(function (th) {
      th.classList.remove('sorted-asc', 'sorted-desc');
      if (th.dataset.sort === wld.sortKey) {
        th.classList.add(wld.sortDir === -1 ? 'sorted-desc' : 'sorted-asc');
      }
    });
  },

  _updateStats() {
    var filtered = this.filtered;
    var cm = 0, td = 0, tp = 0, eq = 0, sess = 0;
    filtered.forEach(function (t) { cm += t.cm_hours; td += t.td_hours; tp += t.tp_hours; eq += t.equivalent_hours; sess += t.total_sessions; });
    document.getElementById('statTeacherCount').textContent = filtered.length;
    document.getElementById('statCM').textContent = cm.toFixed(1);
    document.getElementById('statTD').textContent = td.toFixed(1);
    document.getElementById('statTP').textContent = tp.toFixed(1);
    document.getElementById('statEquivalent').textContent = eq.toFixed(1);
    document.getElementById('statSessions').textContent = sess;
  },

  /* ── Charts ── */

  _renderCharts() {
    this._renderBarChart();
    this._renderPieChart();
  },

  _renderBarChart() {
    var top = this.filtered.slice(0, 15);
    var labels = top.map(function (t) { return t.first_name + ' ' + t.last_name; });
    var eqData = top.map(function (t) { return t.equivalent_hours; });

    if (this.barChart) { this.barChart.destroy(); this.barChart = null; }

    var ctx = document.getElementById('wldBarChart');
    if (!ctx) return;
    if (!labels.length) return;

    this.barChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Charge équivalente (h)',
          data: eqData,
          backgroundColor: 'rgba(242, 140, 40, 0.75)',
          borderColor: '#F28C28',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, title: { display: true, text: 'Heures équivalentes' } },
          y: { ticks: { font: { size: 10 } } }
        }
      }
    });
  },

  _renderPieChart() {
    var filtered = this.filtered;
    var cm = 0, td = 0, tp = 0;
    filtered.forEach(function (t) { cm += t.cm_hours; td += t.td_hours; tp += t.tp_hours; });

    if (this.pieChart) { this.pieChart.destroy(); this.pieChart = null; }

    var ctx = document.getElementById('wldPieChart');
    if (!ctx) return;
    if (cm === 0 && td === 0 && tp === 0) return;

    this.pieChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Cours (CM)', 'TD', 'TP'],
        datasets: [{
          data: [cm, td, tp],
          backgroundColor: ['rgba(15, 125, 184, 0.8)', 'rgba(14, 165, 233, 0.8)', 'rgba(245, 158, 11, 0.8)'],
          borderColor: ['#0F7DB8', '#0ea5e9', '#f59e0b'],
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var total = cm + td + tp;
                var pct = total > 0 ? (ctx.parsed / total * 100).toFixed(1) : 0;
                return ctx.label + ': ' + ctx.parsed.toFixed(1) + 'h (' + pct + '%)';
              }
            }
          }
        }
      }
    });
  },

  /* ── Export Excel ── */

  async exportExcel() {
    try {
      var params = this._buildParams();
      var qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      var url = '/api/v1/teacher-monthly-report/' + (qs ? '?' + qs : '');
      var blob = await API.apiFetch(url);
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      var now = new Date();
      a.download = 'Charge_Horaire_Enseignants_' + String(now.getMonth() + 1).padStart(2, '0') + '_' + now.getFullYear() + '.xlsx';
      a.click();
      URL.revokeObjectURL(a.href);
      showToast('Rapport Excel téléchargé.', 'success');
    } catch (e) {
      showToast('Erreur export: ' + e.message, 'error');
    }
  }
};

/* ── Init ── */
(function () {
  // Bind sort clicks
  document.addEventListener('click', function (e) {
    var th = e.target.closest('.sortable');
    if (th) wld.setSort(th.dataset.sort);
  });

  // Bind export button
  document.getElementById('btnExportExcel')?.addEventListener('click', function () { wld.exportExcel(); });

  wld.init();
})();
