(function () {
  'use strict';

  window.SessionForm = {
    isAdmin: false,
    userRole: null,
    classeId: null,
    blocksData: [],
    amphiData: [],
    teachersData: [],

    /* ── PUBLIC API ── */

    async init(options) {
      this.isAdmin = options && options.isAdmin === true;
      this.userRole = (options && options.userRole) || null;
      this._ensureModal();
      var needsTeacher = this.userRole !== 'teacher';
      await Promise.all([
        this._loadBlocksAmphis(),
        this._loadNiveaux(),
        needsTeacher ? this._loadTeachers() : Promise.resolve(),
      ]);
      this._bindEvents();
    },

    async open(classeId) {
      this.classeId = classeId || null;
      this._reset();
      document.getElementById('sfDate').value = new Date().toISOString().split('T')[0];
      // Reload data if initial load failed or was empty
      const niveauSel = document.getElementById('sfNiveau');
      if (niveauSel.options.length <= 1) await this._loadNiveaux();
      if (!this.blocksData.length || !this.amphiData.length) {
        await this._loadBlocksAmphis();
        this._populateLocationSelects();
      }
      openModal('modalSessionForm');
    },

    /* ── MODAL HTML ── */

    _ensureModal() {
      if (document.getElementById('modalSessionForm')) return;
      const html = `
<div class="modal-backdrop" id="modalSessionForm">
  <div class="modal">
    <div class="modal-header">
      <h3>Nouvelle séance</h3>
      <button class="modal-close" data-close="modalSessionForm">✕</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label>Niveau</label>
        <select id="sfNiveau"><option value="">— Sélectionner —</option></select>
      </div>
      <div class="field">
        <label>Semestre</label>
        <select id="sfSemestre" disabled><option value="">— Sélectionnez d'abord le niveau —</option></select>
        <span class="spinner" id="sfSemestreSpinner" style="display:none"></span>
      </div>
      <div class="field">
        <label>Filière</label>
        <select id="sfFiliere" disabled><option value="">— Sélectionnez d'abord le semestre —</option></select>
        <span class="spinner" id="sfFiliereSpinner" style="display:none"></span>
      </div>
      <div class="field">
        <label>Module</label>
        <select id="sfModule" disabled><option value="">— Sélectionnez d'abord la filière —</option></select>
        <span class="spinner" id="sfModuleSpinner" style="display:none"></span>
      </div>
      <div class="field">
        <label>Type de lieu</label>
        <select id="sfLocationType">
          <option value="">— Sélectionner —</option>
          <option value="block">Bloc / Salle</option>
          <option value="amphitheater">Amphithéâtre</option>
        </select>
      </div>
      <div id="sfBlockGroup" style="display:none">
        <div class="field">
          <label>Bloc</label>
          <select id="sfBlock"><option value="">— Sélectionner un bloc —</option></select>
        </div>
        <div class="field">
          <label>Salle</label>
          <select id="sfRoom" disabled><option value="">— Sélectionner d'abord le bloc —</option></select>
        </div>
      </div>
      <div id="sfAmphiGroup" style="display:none">
        <div class="field">
          <label>Amphithéâtre</label>
          <select id="sfAmphi"><option value="">— Sélectionner un amphithéâtre —</option></select>
        </div>
      </div>
      <div class="field" id="sfTeacherField"${this.userRole !== 'teacher' ? '' : ' style="display:none"'}>
        <label>Enseignant</label>
        <select id="sfTeacher"><option value="">— Sélectionner —</option></select>
      </div>
      <div class="field">
        <label>Type de séance</label>
        <select id="sfSessionType">
          <option value="Cours">Cours</option>
          <option value="TD">TD</option>
          <option value="TP">TP</option>
          <option value="Exam">Examen</option>
          <option value="Other">Autre</option>
        </select>
      </div>
      <div class="field">
        <label>Date</label>
        <input type="date" id="sfDate" />
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        <div class="field">
          <label>Heure de début</label>
          <input type="time" id="sfStartTime" value="14:00" />
        </div>
        <div class="field">
          <label>Heure de fin</label>
          <input type="time" id="sfEndTime" value="16:00" />
        </div>
      </div>
      <p style="font-size:.78rem;color:var(--muted);margin:0">
        Le QR ne peut être généré que pendant ce créneau. Après la fin, seules les statistiques et l'export restent disponibles.
      </p>
    </div>
    <div class="modal-footer">
      <button class="btn outline" data-close="modalSessionForm">Annuler</button>
      <button class="btn" id="sfSubmit">Créer la séance</button>
    </div>
  </div>
</div>`;
      document.body.insertAdjacentHTML('beforeend', html);
    },

    /* ── DATA LOADING ── */

    async _loadNiveaux() {
      const sel = document.getElementById('sfNiveau');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      try {
        const data = await API.apiFetch('/curriculum/niveaux/');
        (data || []).forEach(function (nv) {
          const opt = document.createElement('option');
          opt.value = nv.id;
          opt.textContent = nv.label;
          sel.appendChild(opt);
        });
      } catch (e) { showToast(e.message, 'error'); }
    },

    async _loadSemestres(niveauId) {
      const sel = document.getElementById('sfSemestre');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      sel.disabled = true;
      document.getElementById('sfFiliere').innerHTML = "<option value=\"\">— Sélectionnez d'abord le semestre —</option>";
      document.getElementById('sfFiliere').disabled = true;
      document.getElementById('sfModule').innerHTML = "<option value=\"\">— Sélectionnez d'abord la filière —</option>";
      document.getElementById('sfModule').disabled = true;
      if (!niveauId) return;
      const spinner = document.getElementById('sfSemestreSpinner');
      if (spinner) spinner.style.display = 'inline-block';
      try {
        const data = await API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveauId));
        (data || []).forEach(function (sem) {
          const opt = document.createElement('option');
          opt.value = sem.id;
          opt.textContent = sem.name;
          sel.appendChild(opt);
        });
        sel.disabled = false;
      } catch (e) { showToast(e.message, 'error'); }
      finally { if (spinner) spinner.style.display = 'none'; }
    },

    async _loadFilieres(semestreId, niveauId) {
      const sel = document.getElementById('sfFiliere');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      sel.disabled = true;
      document.getElementById('sfModule').innerHTML = "<option value=\"\">— Sélectionnez d'abord la filière —</option>";
      document.getElementById('sfModule').disabled = true;
      if (!semestreId || !niveauId) return;
      const spinner = document.getElementById('sfFiliereSpinner');
      if (spinner) spinner.style.display = 'inline-block';
      try {
        const params = new URLSearchParams({ semestre_id: semestreId, niveau: niveauId });
        const data = await API.apiFetch('/curriculum/filieres/?' + params.toString());
        (data || []).forEach(function (f) {
          const opt = document.createElement('option');
          opt.value = f.id;
          opt.textContent = f.name;
          sel.appendChild(opt);
        });
        sel.disabled = false;
      } catch (e) { showToast(e.message, 'error'); }
      finally { if (spinner) spinner.style.display = 'none'; }
    },

    async _loadModules(filiereId) {
      const sel = document.getElementById('sfModule');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      sel.disabled = true;
      if (!filiereId) return;
      const spinner = document.getElementById('sfModuleSpinner');
      if (spinner) spinner.style.display = 'inline-block';
      try {
        const data = await API.apiFetch('/curriculum/modules/?filiere_id=' + encodeURIComponent(filiereId));
        (data || []).forEach(function (m) {
          const opt = document.createElement('option');
          opt.value = m.id;
          opt.textContent = m.name;
          sel.appendChild(opt);
        });
        sel.disabled = false;
      } catch (e) { showToast(e.message, 'error'); }
      finally { if (spinner) spinner.style.display = 'none'; }
    },

    async _loadBlocksAmphis() {
      try {
        const [blocks, amphis] = await Promise.all([
          API.apiFetch('/blocks/'),
          API.apiFetch('/amphitheaters/'),
        ]);
        this.blocksData = Array.isArray(blocks) ? blocks : [];
        this.amphiData = Array.isArray(amphis) ? amphis : [];
        this._populateLocationSelects();
      } catch (e) {
        this.blocksData = [];
        this.amphiData = [];
      }
    },

    /* ── AVAILABILITY ── */

    async _fetchAvailableRooms() {
      const date = document.getElementById('sfDate').value;
      const startTime = document.getElementById('sfStartTime').value;
      const endTime = document.getElementById('sfEndTime').value;
      const locType = document.getElementById('sfLocationType').value;
      if (!date || !startTime || !endTime || !locType) return;

      try {
        const params = new URLSearchParams({
          date: date,
          start_time: startTime,
          end_time: endTime,
          location_type: locType,
        });
        const data = await API.apiFetch('/sessions/available-rooms/?' + params.toString());

        if (locType === 'block' && data && data.blocks) {
          this._availableBlocks = data.blocks;
          this._populateBlockSelects(data.blocks);
          // Clear room selection if current room is no longer available
          this._validateCurrentSelection('sfBlock', 'sfRoom', data.blocks);
        } else if (locType === 'amphitheater' && data && data.amphitheaters) {
          this._availableAmphis = data.amphitheaters;
          this._populateAmphiSelect(data.amphitheaters);
          this._validateCurrentSelection('sfAmphi', null, data.amphitheaters);
        }
      } catch (e) {
        // Fall back to full lists on error
        this._populateLocationSelects();
      }
    },

    _populateBlockSelects(blocks) {
      const blockSel = document.getElementById('sfBlock');
      const currentBlock = blockSel.value;
      blockSel.innerHTML = '<option value="">— Sélectionner un bloc —</option>';
      var hasRooms = false;
      blocks.forEach(function (b) {
        if (b.rooms && b.rooms.length) {
          hasRooms = true;
          const opt = document.createElement('option');
          opt.value = b.id;
          opt.textContent = b.name + ' (' + b.rooms.length + ' salle' + (b.rooms.length > 1 ? 's' : '') + ' disponible' + (b.rooms.length > 1 ? 's' : '') + ')';
          blockSel.appendChild(opt);
        }
      });
      if (!hasRooms) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '— Aucune salle disponible —';
        opt.disabled = true;
        blockSel.appendChild(opt);
      }
      // Restore previous selection if still available
      if (currentBlock && blocks.some(function (b) { return String(b.id) === currentBlock; })) {
        blockSel.value = currentBlock;
      }
      blockSel.dispatchEvent(new Event('change'));
    },

    _populateAmphiSelect(amphis) {
      const sel = document.getElementById('sfAmphi');
      const currentVal = sel.value;
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      (amphis || []).forEach(function (a) {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        sel.appendChild(opt);
      });
      if (!amphis || !amphis.length) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '— Aucun amphithéâtre disponible —';
        opt.disabled = true;
        sel.appendChild(opt);
      }
      if (currentVal && amphis.some(function (a) { return String(a.id) === currentVal; })) {
        sel.value = currentVal;
      }
    },

    _validateCurrentSelection(parentId, childId, availableList) {
      if (!availableList || !availableList.length) return;
      if (childId) {
        var parentSel = document.getElementById(parentId);
        var childSel = document.getElementById(childId);
        if (parentSel.value && childSel.value) {
          var block = availableList.find(function (b) { return String(b.id) === parentSel.value; });
          if (block && !block.rooms.some(function (r) { return String(r.id) === childSel.value; })) {
            childSel.value = '';
          }
        }
      } else {
        var sel = document.getElementById(parentId);
        if (sel.value && !availableList.some(function (a) { return String(a.id) === sel.value; })) {
          sel.value = '';
        }
      }
    },

    async _loadTeachers() {
      const sel = document.getElementById('sfTeacher');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      try {
        const data = await API.apiFetch('/teachers/');
        this.teachersData = Array.isArray(data) ? data : [];
        this.teachersData.forEach(function (t) {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = t.full_name + (t.email ? ' (' + t.email + ')' : '');
          sel.appendChild(opt);
        });
      } catch (e) { showToast(e.message, 'error'); }
    },

    /* ── UI HELPERS ── */

    _populateLocationSelects() {
      const blockSel = document.getElementById('sfBlock');
      blockSel.innerHTML = '<option value="">— Sélectionner un bloc —</option>';
      this.blocksData.forEach(function (b) {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.name;
        blockSel.appendChild(opt);
      });
      const amphiSel = document.getElementById('sfAmphi');
      amphiSel.innerHTML = '<option value="">— Sélectionner un amphithéâtre —</option>';
      this.amphiData.forEach(function (a) {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        amphiSel.appendChild(opt);
      });
    },

    _reset() {
      const now = new Date();
      const y = now.getFullYear();
      const m = now.getMonth() + 1;
      const d = now.getDate();
      document.getElementById('sfDate').value = y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      document.getElementById('sfStartTime').value = '14:00';
      document.getElementById('sfEndTime').value = '16:00';
      document.getElementById('sfLocationType').value = '';
      document.getElementById('sfBlockGroup').style.display = 'none';
      document.getElementById('sfAmphiGroup').style.display = 'none';
      document.getElementById('sfBlock').innerHTML = '<option value="">— Sélectionner un bloc —</option>';
      document.getElementById('sfRoom').innerHTML = "<option value=\"\">— Sélectionner d'abord le bloc —</option>";
      document.getElementById('sfRoom').disabled = true;
      document.getElementById('sfAmphi').innerHTML = '<option value="">— Sélectionner un amphithéâtre —</option>';
      document.getElementById('sfSessionType').value = 'Cours';
      this._populateLocationSelects();
      this._resetCascade(0);
    },

    _resetCascade(level) {
      const semestre = document.getElementById('sfSemestre');
      const filiere = document.getElementById('sfFiliere');
      const module = document.getElementById('sfModule');
      if (level <= 0) {
        semestre.innerHTML = "<option value=\"\">— Sélectionnez d'abord le niveau —</option>";
        semestre.disabled = true;
      }
      if (level <= 1) {
        filiere.innerHTML = "<option value=\"\">— Sélectionnez d'abord le semestre —</option>";
        filiere.disabled = true;
      }
      if (level <= 2) {
        module.innerHTML = "<option value=\"\">— Sélectionnez d'abord la filière —</option>";
        module.disabled = true;
      }
    },

    /* ── EVENT BINDING ── */

    _bindEvents() {
      const self = this;

      document.getElementById('sfNiveau').addEventListener('change', function () {
        self._resetCascade(0);
        self._loadSemestres(this.value);
      });

      document.getElementById('sfSemestre').addEventListener('change', function () {
        const niveauId = document.getElementById('sfNiveau').value;
        self._resetCascade(1);
        self._loadFilieres(this.value, niveauId);
      });

      document.getElementById('sfFiliere').addEventListener('change', function () {
        self._resetCascade(2);
        self._loadModules(this.value);
      });

      document.getElementById('sfLocationType').addEventListener('change', function () {
        const val = this.value;
        document.getElementById('sfBlockGroup').style.display = val === 'block' ? 'block' : 'none';
        document.getElementById('sfAmphiGroup').style.display = val === 'amphitheater' ? 'block' : 'none';
        // When location type changes, restore full lists first, then filter by availability
        self._populateLocationSelects();
        self._fetchAvailableRooms();
      });

      // Re-check availability when date or time changes
      ['sfDate', 'sfStartTime', 'sfEndTime'].forEach(function (id) {
        document.getElementById(id).addEventListener('change', function () {
          const locType = document.getElementById('sfLocationType').value;
          if (locType) {
            // Restore full lists and filter
            self._populateLocationSelects();
            self._fetchAvailableRooms();
          }
        });
      });

      document.getElementById('sfBlock').addEventListener('change', function () {
        const blockId = parseInt(this.value);
        const roomSel = document.getElementById('sfRoom');
        roomSel.innerHTML = '<option value="">— Sélectionner —</option>';
        roomSel.disabled = !blockId;
        if (blockId) {
          const block = self.blocksData.find(function (b) { return b.id === blockId; });
          if (block && block.rooms) {
            block.rooms.forEach(function (r) {
              const opt = document.createElement('option');
              opt.value = r.id;
              opt.textContent = r.name;
              roomSel.appendChild(opt);
            });
          }
        }
      });

      document.getElementById('sfSubmit').addEventListener('click', function () { self._submit(); });
    },

    /* ── SUBMIT ── */

    async _submit() {
      const moduleEl = document.getElementById('sfModule');
      const moduleId = moduleEl.value;
      const locType = document.getElementById('sfLocationType').value;
      const date = document.getElementById('sfDate').value;
      const startTime = document.getElementById('sfStartTime').value;
      const endTime = document.getElementById('sfEndTime').value;

      if (!moduleId) { showToast('Veuillez sélectionner un module.', 'error'); return; }
      if (!date || !startTime || !endTime) { showToast('Date et horaires obligatoires.', 'error'); return; }
      if (endTime <= startTime) { showToast("L'heure de fin doit être après l'heure de début.", 'error'); return; }
      if (!locType) { showToast('Veuillez sélectionner un type de lieu.', 'error'); return; }

      const body = {
        module_id: Number(moduleId),
        date: date,
        start_time: startTime,
        end_time: endTime,
        location_type: locType,
        session_type: document.getElementById('sfSessionType').value,
      };

      if (this.classeId) {
        body.classe = this.classeId;
      }

      if (locType === 'block') {
        const blockId = document.getElementById('sfBlock').value;
        const roomId = document.getElementById('sfRoom').value;
        if (!blockId) { showToast('Veuillez sélectionner un bloc.', 'error'); return; }
        if (!roomId) { showToast('Veuillez sélectionner une salle.', 'error'); return; }
        body.block = Number(blockId);
        body.room = Number(roomId);
      } else if (locType === 'amphitheater') {
        const amphiId = document.getElementById('sfAmphi').value;
        if (!amphiId) { showToast('Veuillez sélectionner un amphithéâtre.', 'error'); return; }
        body.amphitheater = Number(amphiId);
      }

      if (this.userRole !== 'teacher') {
        const teacherVal = document.getElementById('sfTeacher').value;
        if (!teacherVal) { showToast('Veuillez sélectionner un enseignant.', 'error'); return; }
        body.teacher = Number(teacherVal);
      }

      const btn = document.getElementById('sfSubmit');
      btn.disabled = true;
      btn.textContent = 'Création…';

      try {
        const session = await API.apiFetch('/sessions/', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        closeModal('modalSessionForm');
        showToast('Séance créée avec succès.', 'success');

        // Notify the page so it can refresh its lists
        var evt = new CustomEvent('session-created', { detail: session });
        document.dispatchEvent(evt);
      } catch (e) {
        showToast('Erreur : ' + (e.message || 'Échec de création de la séance.'), 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Créer la séance';
      }
    },
  };
})();
