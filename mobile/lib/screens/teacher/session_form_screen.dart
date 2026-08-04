import 'package:flutter/material.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../models/classe_model.dart';
import '../../models/session_model.dart';
import '../../services/teacher_service.dart';

/// Formulaire de création / modification d'une séance.
class SessionFormScreen extends StatefulWidget {
  final SessionModel? session;

  const SessionFormScreen({super.key, this.session});

  @override
  State<SessionFormScreen> createState() => _SessionFormScreenState();
}

class _SessionFormScreenState extends State<SessionFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _teacherService = TeacherService();

  bool _isEdit = false;
  bool _loading = false;
  bool _submitting = false;
  String? _error;
  AvailableLocations? _available;

  late DateTime _date;
  late TimeOfDay _startTime;
  late TimeOfDay _endTime;

  ClasseModel? _selectedClasse;
  SessionType _sessionType = SessionType.cours;
  LocationType _locationType = LocationType.block;

  List<ClasseModel> _classes = [];
  List<BlockModel> _blocks = [];
  List<AmphitheaterModel> _amphitheaters = [];

  BlockModel? _selectedBlock;
  BlockRoom? _selectedRoom;
  AmphitheaterModel? _selectedAmphi;

  @override
  void initState() {
    super.initState();
    _isEdit = widget.session != null;
    _date = DateTime.now();
    _startTime = const TimeOfDay(hour: 14, minute: 0);
    _endTime = const TimeOfDay(hour: 16, minute: 0);

    if (_isEdit) {
      final s = widget.session!;
      _date = DateTime.tryParse(s.date) ?? DateTime.now();
      _startTime = _parseTime(s.startTime);
      _endTime = _parseTime(s.endTime);
      _sessionType = s.sessionTypeEnum;
      _locationType = LocationType.fromApi(s.locationType);
    }
    _init();
  }

  TimeOfDay _parseTime(String t) {
    final parts = t.split(':');
    if (parts.length >= 2) {
      return TimeOfDay(hour: int.tryParse(parts[0]) ?? 0, minute: int.tryParse(parts[1]) ?? 0);
    }
    return const TimeOfDay(hour: 14, minute: 0);
  }

  String _two(int n) => n.toString().padLeft(2, '0');
  String get _dateStr =>
      '${_date.year}-${_two(_date.month)}-${_two(_date.day)}';
  String get _startStr =>
      '${_two(_startTime.hour)}:${_two(_startTime.minute)}:00';
  String get _endStr => '${_two(_endTime.hour)}:${_two(_endTime.minute)}:00';

  Future<void> _init() async {
    setState(() => _loading = true);
    try {
      _classes = await _teacherService.fetchClasses();
      final blocks = await _teacherService.fetchBlocks();
      final amphis = await _teacherService.fetchAmphitheaters();
      setState(() {
        _blocks = blocks;
        _amphitheaters = amphis;
      });
      if (_isEdit) {
        final s = widget.session!;
        if (s.classe != null) {
          _selectedClasse = _classes.firstWhere(
            (c) => c.id == s.classe,
            orElse: () => _classes.isNotEmpty ? _classes.first : _ClassePlaceholder(),
          );
        }
        _selectedBlock = blocks.firstWhereOrNull((b) => b.id == s.block);
        if (_selectedBlock != null) {
          _selectedRoom = _selectedBlock!.rooms.firstWhereOrNull((r) => r.id == s.room);
        }
        _selectedAmphi = amphis.firstWhereOrNull((a) => a.id == s.amphitheater);
      } else if (_classes.isNotEmpty) {
        _selectedClasse = _classes.first;
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
    _fetchAvailability();
  }

  Future<void> _fetchAvailability() async {
    try {
      final available = await _teacherService.fetchAvailableLocations(
        date: _dateStr,
        startTime: _startStr,
        endTime: _endStr,
        locationType: _locationType.apiValue,
        excludeSessionId: widget.session?.id,
      );
      setState(() => _available = available);
    } catch (_) {
      // Disponibilités optionnelles
    }
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_selectedClasse == null) {
      setState(() => _error = 'Sélectionnez une classe.');
      return;
    }
    if (_locationType == LocationType.block && _selectedRoom == null) {
      setState(() => _error = 'Sélectionnez une salle.');
      return;
    }
    if (_locationType == LocationType.amphitheater && _selectedAmphi == null) {
      setState(() => _error = 'Sélectionnez un amphithéâtre.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    final payload = <String, dynamic>{
      'classe': _selectedClasse!.id,
      'date': _dateStr,
      'start_time': _startStr,
      'end_time': _endStr,
      'location_type': _locationType.apiValue,
      'session_type': _sessionType.apiValue,
      if (_locationType == LocationType.block) 'block': _selectedBlock?.id,
      if (_locationType == LocationType.block) 'room': _selectedRoom!.id,
      if (_locationType != LocationType.block) 'amphitheater': _selectedAmphi!.id,
    };
    // Le module est dérivé de la classe côté serveur si absent
    if (_selectedClasse!.moduleId != null) {
      payload['module_id'] = _selectedClasse!.moduleId;
    }

    try {
      if (_isEdit) {
        await _teacherService.updateSession(widget.session!.id, payload);
      } else {
        final createdSession = await _teacherService.createSession(payload);
        if (!mounted) return;
        // Navigate to QR generation screen for the newly created session
        Navigator.of(context).pushReplacementNamed(
          AppConstants.routeGenerateQr,
          arguments: createdSession.id,
        );
      }
      if (!mounted) return;
      // Show success message (optional)
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_isEdit ? 'Séance modifiée avec succès' : 'Séance créée avec succès'),
          backgroundColor: AppTheme.successColor,
        ),
      );
      // Navigation handled above for creation; for edit, just pop.
      if (_isEdit) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isEdit ? 'Modifier la séance' : 'Nouvelle séance'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null)
                    Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.errorColor.withOpacity(.08),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline,
                              color: AppTheme.errorColor, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(_error!,
                                style: const TextStyle(fontSize: 12)),
                          ),
                        ],
                      ),
                    ),

                  // ── Classe ────────────────────────────────────────────
                  DropdownButtonFormField<int>(
                    initialValue: _selectedClasse?.id,
                    decoration: const InputDecoration(labelText: 'Classe / Module'),
                    items: _classes
                        .map((c) => DropdownMenuItem(
                              value: c.id,
                              child: Text(
                                c.name,
                                style: const TextStyle(fontSize: 13),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ))
                        .toList(),
                    onChanged: _isEdit
                        ? null
                        : (v) {
                            setState(() {
                              _selectedClasse = _classes
                                  .firstWhere((c) => c.id == v);
                            });
                          },
                    validator: (v) => v == null ? 'Classe requise' : null,
                  ),
                  const SizedBox(height: 16),

                  // ── Type de séance ────────────────────────────────────
                  DropdownButtonFormField<SessionType>(
                    initialValue: _sessionType,
                    decoration: const InputDecoration(labelText: 'Type de séance'),
                    items: SessionType.values
                        .map((t) => DropdownMenuItem(
                              value: t,
                              child: Text(t.label),
                            ))
                        .toList(),
                    onChanged: (v) =>
                        setState(() => _sessionType = v ?? SessionType.cours),
                  ),
                  const SizedBox(height: 16),

                  // ── Date ──────────────────────────────────────────────
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.calendar_today_outlined),
                    title: const Text('Date'),
                    subtitle: Text(_dateStr),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: _date,
                        firstDate: DateTime.now().subtract(const Duration(days: 1)),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (picked != null) {
                        setState(() => _date = picked);
                        _fetchAvailability();
                      }
                    },
                  ),
                  const SizedBox(height: 8),

                  // ── Heures ────────────────────────────────────────────
                  Row(
                    children: [
                      Expanded(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.access_time_rounded),
                          title: const Text('Début'),
                          subtitle: Text(_startTime.format(context)),
                          onTap: () async {
                            final picked = await showTimePicker(
                              context: context,
                              initialTime: _startTime,
                            );
                            if (picked != null) {
                              setState(() => _startTime = picked);
                              _fetchAvailability();
                            }
                          },
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.access_time_filled_rounded),
                          title: const Text('Fin'),
                          subtitle: Text(_endTime.format(context)),
                          onTap: () async {
                            final picked = await showTimePicker(
                              context: context,
                              initialTime: _endTime,
                            );
                            if (picked != null) {
                              setState(() => _endTime = picked);
                              _fetchAvailability();
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // ── Type de lieu ──────────────────────────────────────
                  SegmentedButton<LocationType>(
                    segments: const [
                      ButtonSegment(
                        value: LocationType.block,
                        label: Text('Bloc / Salle'),
                        icon: Icon(Icons.apartment_rounded),
                      ),
                      ButtonSegment(
                        value: LocationType.amphitheater,
                        label: Text('Amphi'),
                        icon: Icon(Icons.theaters_rounded),
                      ),
                    ],
                    selected: {_locationType},
                    onSelectionChanged: (v) {
                      setState(() => _locationType = v.first);
                      _fetchAvailability();
                    },
                  ),
                  if (_available != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12, bottom: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.check_circle_outline,
                              size: 16, color: AppTheme.primary),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              _available!.rooms.isEmpty &&
                                      _available!.amphitheaters.isEmpty
                                  ? 'Aucun lieu disponible à ces horaires'
                                  : '${_available!.rooms.length} salles et '
                                      '${_available!.amphitheaters.length} '
                                      'amphis disponibles',
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey[600]),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 12),

    // ── Lieu ──────────────────────────────────────────────
                    if (_locationType == LocationType.block) ...[
                      DropdownButtonFormField<int>(
                        initialValue: _selectedBlock?.id,
                        decoration: const InputDecoration(labelText: 'Bloc'),
                        items: _blocks
                            .map((b) => DropdownMenuItem(
                                  value: b.id,
                                  child: Text(b.name),
                                ))
                            .toList(),
                        onChanged: (v) {
                          setState(() {
                            _selectedBlock =
                                _blocks.firstWhere((b) => b.id == v);
                            _selectedRoom = null;
                          });
                        },
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<int>(
                        initialValue: _selectedRoom?.id,
                        decoration: const InputDecoration(labelText: 'Salle'),
                        items: (_selectedBlock?.rooms ?? [])
                            .map((r) => DropdownMenuItem(
                                  value: r.id,
                                  child: Text(r.name),
                                ))
                            .toList(),
                        onChanged: (v) {
                          setState(() {
                            _selectedRoom = _selectedBlock!.rooms
                                .firstWhere((r) => r.id == v);
                          });
                        },
                        validator: (v) => v == null ? 'Salle requise' : null,
                      ),
                    ] else
                      DropdownButtonFormField<int>(
                        initialValue: _selectedAmphi?.id,
                        decoration:
                            const InputDecoration(labelText: 'Amphithéâtre'),
                        items: _amphitheaters
                            .map((a) => DropdownMenuItem(
                                  value: a.id,
                                  child: Text(a.name),
                                ))
                            .toList(),
                        onChanged: (v) {
                          setState(() {
                            _selectedAmphi = _amphitheaters
                                .firstWhere((a) => a.id == v);
                          });
                        },
                        validator: (v) => v == null ? 'Amphithéâtre requis' : null,
                      ),

                  // ── Submit ────────────────────────────────────────────
                  ElevatedButton.icon(
                    onPressed: _submitting ? null : _submit,
                    icon: _submitting
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : Icon(_isEdit
                            ? Icons.save_rounded
                            : Icons.add_rounded),
                    label: Text(_isEdit ? 'Enregistrer' : 'Créer la séance'),
                  ),
                ],
              ),
            ),
    );
  }
}

class _ClassePlaceholder extends ClasseModel {
  _ClassePlaceholder()
      : super(id: -1, name: '—', niveau: '', code: '');
}

extension _FirstWhereOrNull on List<BlockModel> {
  BlockModel? firstWhereOrNull(bool Function(BlockModel) test) {
    for (final e in this) {
      if (test(e)) return e;
    }
    return null;
  }
}

extension _AmphiFirstWhereOrNull on List<AmphitheaterModel> {
  AmphitheaterModel? firstWhereOrNull(bool Function(AmphitheaterModel) test) {
    for (final e in this) {
      if (test(e)) return e;
    }
    return null;
  }
}

extension _RoomFirstWhereOrNull on List<BlockRoom> {
  BlockRoom? firstWhereOrNull(bool Function(BlockRoom) test) {
    for (final e in this) {
      if (test(e)) return e;
    }
    return null;
  }
}
