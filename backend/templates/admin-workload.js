/* ── Teacher Workload Dashboard ── */

var wld = {
  data: null,
  teachers: [],
  totals: {},
  chartData: {},
  filtered: [],
  sortKey: 'equivalent',
  sortDir: -1,
  page: 0,
  pageSize: 15,
  barChart: null,
  pieChart: null,
  deptChart: null,
  filiereChart: null,
  stackedChart: null,
  monthlyChart: null,

  async init() {
    await Promise.all([
      this._loadDepts(),
      this._loadFilieres(),
      this._loadAcademicYears(),
      this._loadTeachers(),
    ]);
    this._loadSemestres();
    this._initPeriod();
    await this.loadData();
  },

  /* ── Load filter options ── */

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

  async _loadFilieres(filiereId) {
    try {
      var deptId = document.getElementById('wldDept').value;
      var url = '/curriculum/filieres/' + (deptId ? '?department_id=' + deptId : '');
      var data = await API.apiFetch(url);
      var fils = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldFiliere');
      sel.innerHTML = '<option value="">Toutes</option>';
      fils.forEach(function (f) {
        var o = document.createElement('option');
        o.value = f.id;
        o.textContent = f.name;
        if (filiereId && String(f.id) === String(filiereId)) o.selected = true;
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

  async _loadSemestres() {
    try {
      var data = await API.apiFetch('/curriculum/semestres/');
      var sems = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldSemestre');
      sems.forEach(function (s) {
        var o = document.createElement('option');
        o.value = s.id;
        o.textContent = s.nom || s.name || ('Semestre ' + s.id);
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadModules(semestreId) {
    try {
      var url = '/curriculum/modules/' + (semestreId ? '?semestre_id=' + semestreId : '');
      var data = await API.apiFetch(url);
      var mods = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldModule');
      sel.innerHTML = '<option value="">Tous</option>';
      mods.forEach(function (m) {
        var o = document.createElement('option');
        o.value = m.id;
        o.textContent = m.name || m.nom || ('Module ' + m.id);
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadTeachers() {
    try {
      var data = await API.apiFetch('/users/?role=teacher');
      var users = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldTeacher');
      sel.innerHTML = '<option value="">Tous</option>';
      users.forEach(function (u) {
        var o = document.createElement('option');
        o.value = u.id;
        o.textContent = (u.first_name || '') + ' ' + (u.last_name || '') + ' (' + (u.email || '') + ')';
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
    this.page = 0;
    this.onFilterChange();
  },

  onFilterChange() {
    this.page = 0;
    this.loadData();
  },

  async onDeptChange() {
    await this._loadFilieres();
    this.page = 0;
    this.onFilterChange();
  },

  async onSemestreChange() {
    await this._loadModules(document.getElementById('wldSemestre').value);
    this.page = 0;
    this.onFilterChange();
  },

  _buildParams() {
    var params = {};
    var dept = document.getElementById('wldDept').value;
    var filiere = document.getElementById('wldFiliere').value;
    var semestre = document.getElementById('wldSemestre').value;
    var module = document.getElementById('wldModule').value;
    var teacher = document.getElementById('wldTeacher').value;
    var year = document.getElementById('wldYear').value;
    var period = document.getElementById('wldPeriod').value;

    if (dept) params.department_id = dept;
    if (filiere) params.filiere_id = filiere;
    if (semestre) params.semestre_id = semestre;
    if (module) params.module_id = module;
    if (teacher) params.teacher_id = teacher;
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
      var url = '/teacher-workload-dashboard/' + (qs ? '?' + qs : '');
      var resp = await API.apiFetch(url);
      this.teachers = resp.teachers || [];
      this.totals = resp.totals || {};
      this.chartData = resp.chart_data || {};
      this._applyFilters();
      this._renderRanking();
      this._renderSummary();
      this._renderTable();
      this._renderCharts();
      this._updateStats();
    } catch (e) {
      document.getElementById('wldBody').innerHTML = '<tr class="empty-row"><td colspan="9">Erreur: ' + API.esc(e.message) + '</td></tr>';
    }
  },

  /* ── Ranking table ── */

  _renderRanking() {
    var tbody = document.getElementById('wldRankingBody');
    if (!tbody) return;
    var data = this.filtered;
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:1rem">Aucune donnée</td></tr>';
      return;
    }
    var medals = ['🥇', '🥈', '🥉'];
    tbody.innerHTML = data.map(function (t, i) {
      var rank = i < 3 ? medals[i] : ('#' + (i + 1));
      return '<tr>' +
        '<td style="text-align:center;font-size:1.1rem">' + rank + '</td>' +
        '<td><strong>' + API.esc(t.first_name) + ' ' + API.esc(t.last_name) + '</strong></td>' +
        '<td style="text-align:right;font-weight:700;color:var(--accent)">' + t.equivalent_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:var(--primary)">' + t.cm_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:#0ea5e9">' + t.td_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:#f59e0b">' + t.tp_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right">' + t.total_sessions + '</td>' +
      '</tr>';
    }).join('');
  },

  /* ── Table ── */

  _applyFilters() {
    this.filtered = this.teachers.slice();
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
    this.page = 0;
    this._renderTable();
  },

  _goToPage(delta) {
    var total = this.filtered.length;
    var maxPage = Math.max(0, Math.ceil(total / this.pageSize) - 1);
    this.page = Math.max(0, Math.min(maxPage, this.page + delta));
    this._renderTable();
  },

  _renderTable() {
    var tbody = document.getElementById('wldBody');
    var info = document.getElementById('wldPaginationInfo');

    if (!this.filtered.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="9">Aucune donnée pour les filtres sélectionnés.</td></tr>';
      if (info) info.textContent = '—';
      return;
    }

    var start = this.page * this.pageSize;
    var end = Math.min(start + this.pageSize, this.filtered.length);
    var pageItems = this.filtered.slice(start, end);

    tbody.innerHTML = pageItems.map(function (t, i) {
      return '<tr>' +
        '<td style="color:var(--muted)">' + (start + i + 1) + '</td>' +
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

    document.querySelectorAll('.sortable').forEach(function (th) {
      th.classList.remove('sorted-asc', 'sorted-desc');
      if (th.dataset.sort === wld.sortKey) {
        th.classList.add(wld.sortDir === -1 ? 'sorted-desc' : 'sorted-asc');
      }
    });

    if (info) {
      info.textContent = 'Affichage ' + (start + 1) + '–' + end + ' sur ' + this.filtered.length + ' enseignant(s)';
    }
  },

  _updateStats() {
    var filtered = this.filtered;
    var cm = 0, td = 0, tp = 0, eq = 0, sess = 0;
    filtered.forEach(function (t) { cm += t.cm_hours; td += t.td_hours; tp += t.tp_hours; eq += t.equivalent_hours; sess += t.total_sessions; });
    var avg = filtered.length > 0 ? eq / filtered.length : 0;
    document.getElementById('statTeacherCount').textContent = filtered.length;
    document.getElementById('statCM').textContent = cm.toFixed(1);
    document.getElementById('statTD').textContent = td.toFixed(1);
    document.getElementById('statTP').textContent = tp.toFixed(1);
    document.getElementById('statEquivalent').textContent = eq.toFixed(1);
    document.getElementById('statAvgEquivalent').textContent = avg.toFixed(1);
    document.getElementById('statSessions').textContent = sess;

    var te = document.getElementById('statTopTeacher');
    if (te) {
      var top = this.totals.top_teacher;
      te.textContent = top ? API.esc(top.name) + ' — ' + top.equivalent_hours.toFixed(1) + 'h' : '—';
    }
  },

  /* ── Summary bars ── */

  _renderSummary() {
    var el = document.getElementById('wldSummary');
    if (!el) return;
    var filtered = this.filtered;
    if (!filtered.length) {
      el.innerHTML = '<div class="empty-row" style="text-align:center;padding:1rem;color:var(--muted)">Aucun enseignant pour les filtres sélectionnés.</div>';
      return;
    }

    var maxEq = filtered.reduce(function (m, t) { return Math.max(m, t.equivalent_hours); }, 0) || 1;
    var color = 'var(--accent)';

    var html = filtered.map(function (t, i) {
      var pct = Math.round((t.equivalent_hours / maxEq) * 100);
      var shortName = API.esc(t.first_name) + ' ' + API.esc(t.last_name);
      var dept = API.esc(t.department || '—');

      return '<div class="summary-row" style="display:flex;align-items:center;gap:10px;padding:5px 10px;border-radius:8px;background:var(--surface-2);font-size:.8rem">' +
        '<span style="width:24px;text-align:right;color:var(--muted);font-weight:600;flex-shrink:0">' + (i + 1) + '</span>' +
        '<div style="flex:0 0 160px;min-width:0">' +
          '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + shortName + '</div>' +
          '<div style="font-size:.68rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + dept + '</div>' +
        '</div>' +
        '<div style="flex:1;min-width:60px;height:22px;background:rgba(255,255,255,0.06);border-radius:5px;overflow:hidden;position:relative">' +
          '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:5px;opacity:.7;transition:width .3s"></div>' +
          '<span style="position:absolute;right:5px;top:50%;transform:translateY(-50%);font-size:.7rem;font-weight:600;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.4)">' + t.equivalent_hours.toFixed(1) + 'h</span>' +
        '</div>' +
        '<div style="flex:0 0 auto;display:flex;gap:6px;font-size:.7rem;white-space:nowrap">' +
          '<span style="color:var(--primary)">CM ' + t.cm_hours.toFixed(1) + '</span>' +
          '<span style="color:#0ea5e9">TD ' + t.td_hours.toFixed(1) + '</span>' +
          '<span style="color:#f59e0b">TP ' + t.tp_hours.toFixed(1) + '</span>' +
        '</div>' +
        '<span style="flex:0 0 36px;text-align:right;color:var(--muted);font-size:.7rem">' + t.total_sessions + ' s.</span>' +
      '</div>';
    }).join('');

    el.innerHTML = html;
  },

  /* ── Charts ── */

  _renderCharts() {
    this._renderBarChart();
    this._renderPieChart();
    this._renderStackedChart();
    this._renderDeptChart();
    this._renderFiliereChart();
    this._renderMonthlyChart();
  },

  _renderBarChart() {
    var labels = this.chartData.labels || [];
    var eqData = this.chartData.equivalent_hours || [];

    if (this.barChart) { this.barChart.destroy(); this.barChart = null; }
    var ctx = document.getElementById('wldBarChart');
    if (!ctx || !labels.length) return;

    // Use all teachers but short labels if too many
    var displayLabels = labels;
    var displayData = eqData;
    if (labels.length > 30) {
      displayLabels = labels.slice(0, 30);
      displayData = eqData.slice(0, 30);
    }

    this.barChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: displayLabels,
        datasets: [{
          label: 'Charge équivalente (h)',
          data: displayData,
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
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (ctx) { return ctx.parsed.x.toFixed(1) + 'h'; } } }
        },
        scales: {
          x: { beginAtZero: true, title: { display: true, text: 'Heures équivalentes' } },
          y: { ticks: { font: { size: 9 } } }
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
    if (!ctx || (cm === 0 && td === 0 && tp === 0)) return;

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

  _renderStackedChart() {
    if (this.stackedChart) { this.stackedChart.destroy(); this.stackedChart = null; }
    var ctx = document.getElementById('wldStackedChart');
    if (!ctx) return;

    var data = this.filtered;
    if (!data.length) return;
    var top = data.slice(0, 15);
    var labels = top.map(function (t) { return t.first_name + ' ' + t.last_name; });

    this.stackedChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          { label: 'CM', data: top.map(function (t) { return t.cm_hours; }), backgroundColor: 'rgba(15, 125, 184, 0.85)', borderRadius: 2 },
          { label: 'TD', data: top.map(function (t) { return t.td_hours; }), backgroundColor: 'rgba(14, 165, 233, 0.85)', borderRadius: 2 },
          { label: 'TP', data: top.map(function (t) { return t.tp_hours; }), backgroundColor: 'rgba(245, 158, 11, 0.85)', borderRadius: 2 },
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, ticks: { font: { size: 9 } } },
          y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Heures' } }
        },
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 10 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + 'h'; }
            }
          }
        }
      }
    });
  },

  _renderDeptChart() {
    if (this.deptChart) { this.deptChart.destroy(); this.deptChart = null; }
    var ctx = document.getElementById('wldDeptChart');
    if (!ctx) return;
    var labels = this.chartData.dept_labels || [];
    var eqData = this.chartData.dept_eq || [];
    if (!labels.length) return;

    this.deptChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Charge équivalente (h)',
          data: eqData,
          backgroundColor: 'rgba(15, 125, 184, 0.7)',
          borderColor: '#0F7DB8',
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

  _renderFiliereChart() {
    if (this.filiereChart) { this.filiereChart.destroy(); this.filiereChart = null; }
    var ctx = document.getElementById('wldFiliereChart');
    if (!ctx) return;
    var labels = this.chartData.filiere_labels || [];
    var eqData = this.chartData.filiere_eq || [];
    if (!labels.length) return;

    this.filiereChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Charge équivalente (h)',
          data: eqData,
          backgroundColor: 'rgba(14, 165, 233, 0.7)',
          borderColor: '#0ea5e9',
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

  _renderMonthlyChart() {
    if (this.monthlyChart) { this.monthlyChart.destroy(); this.monthlyChart = null; }
    var ctx = document.getElementById('wldMonthlyChart');
    if (!ctx) return;
    var labels = this.chartData.monthly_labels || [];
    if (!labels.length) return;

    this.monthlyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'CM',
            data: this.chartData.monthly_cm || [],
            borderColor: '#0F7DB8',
            backgroundColor: 'rgba(15, 125, 184, 0.1)',
            fill: false,
            tension: 0.3,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
          {
            label: 'TD',
            data: this.chartData.monthly_td || [],
            borderColor: '#0ea5e9',
            backgroundColor: 'rgba(14, 165, 233, 0.1)',
            fill: false,
            tension: 0.3,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
          {
            label: 'TP',
            data: this.chartData.monthly_tp || [],
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            fill: false,
            tension: 0.3,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 10 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + 'h'; }
            }
          }
        },
        scales: {
          x: { ticks: { font: { size: 10 } } },
          y: { beginAtZero: true, title: { display: true, text: 'Heures' } }
        }
      }
    });
  },

  /* ── Export Excel ── */

  async exportExcel() {
    try {
      var params = this._buildParams();
      var qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      var url = '/teacher-monthly-report/' + (qs ? '?' + qs : '');
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

/* ── Bind events (call wld.init() to start) ── */
wld.bindEvents = function () {
  document.addEventListener('click', function (e) {
    var th = e.target.closest('.sortable');
    if (th) wld.setSort(th.dataset.sort);
  });

  document.getElementById('btnExportExcel')?.addEventListener('click', function () { wld.exportExcel(); });

  document.getElementById('wldPagePrev')?.addEventListener('click', function () { wld._goToPage(-1); });
  document.getElementById('wldPageNext')?.addEventListener('click', function () { wld._goToPage(1); });

  document.getElementById('wldDept')?.addEventListener('change', function () { wld.onDeptChange(); });
  document.getElementById('wldSemestre')?.addEventListener('change', function () { wld.onSemestreChange(); });
  document.getElementById('wldFiliere')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldModule')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldTeacher')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldYear')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldPeriod')?.addEventListener('change', function () { wld.onPeriodChange(); });
  document.getElementById('wldMonth')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldDateStart')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldDateEnd')?.addEventListener('change', function () { wld.onFilterChange(); });
};
