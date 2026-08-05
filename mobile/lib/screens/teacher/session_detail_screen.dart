import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../models/session_model.dart';
import '../../providers/teacher_provider.dart';
import '../../services/file_share_service.dart';
import '../../services/teacher_service.dart';
import '../../utils/app_exceptions.dart';

/// Détail d'une séance : QR, présences, statistiques, tentatives suspectes.
class SessionDetailScreen extends StatefulWidget {
  final int sessionId;

  const SessionDetailScreen({super.key, required this.sessionId});

  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TeacherProvider>().loadSessionDetail(widget.sessionId);
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _exportPresenceSheet(TeacherProvider provider) async {
    final session = provider.selectedSession;
    final messenger = ScaffoldMessenger.of(context);
    try {
      final subject = (session?.subject.isNotEmpty ?? false)
          ? session!.subject
          : 'seance';
      final safeSubject = subject.replaceAll(RegExp(r'[^a-zA-Z0-9_-]+'), '_');
      final filename =
          'presence_${safeSubject}_${session?.date ?? widget.sessionId}.xlsx';
      final bytes = await TeacherService().exportSessionXlsx(widget.sessionId);
      await FileShareService.shareXlsx(bytes, filename);
    } on AppException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(content: Text('Export indisponible')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    final session = provider.selectedSession;

    return Scaffold(
      appBar: AppBar(
        title: Text(session?.subject ?? 'Séance'),
        actions: [
          IconButton(
            icon: const Icon(Icons.grid_on_rounded),
            tooltip: 'Feuille de présence (Excel)',
            onPressed: session == null
                ? null
                : () => _exportPresenceSheet(provider),
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_2_rounded),
            tooltip: 'Générer le QR',
            onPressed: () => Navigator.of(context).pushNamed(
              AppConstants.routeGenerateQr,
              arguments: session?.id ?? widget.sessionId,
            ),
          ),
        ],
      ),
      body: provider.sessionDetailLoading && session == null
          ? const Center(child: CircularProgressIndicator())
          : session == null
              ? _ErrorView(
                  message: provider.sessionDetailError ?? 'Erreur',
                  onRetry: () =>
                      provider.loadSessionDetail(widget.sessionId),
                )
              : Column(
                  children: [
                    _SessionHeader(session: session),
                    TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      tabAlignment: TabAlignment.start,
                      tabs: const [
                        Tab(text: 'Présences'),
                        Tab(text: 'Carte'),
                        Tab(text: 'QR'),
                        Tab(text: 'Statistiques'),
                        Tab(text: 'Suspects'),
                      ],
                    ),
                    Expanded(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          _AttendanceTab(sessionId: widget.sessionId),
                          _MapTab(sessionId: widget.sessionId),
                          _QrTab(sessionId: widget.sessionId),
                          _StatsTab(sessionId: widget.sessionId),
                          _SuspiciousTab(sessionId: widget.sessionId),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }
}

class _SessionHeader extends StatelessWidget {
  final SessionModel session;
  const _SessionHeader({required this.session});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(session.classeName.isNotEmpty
              ? session.classeName
              : session.classeField),
          const SizedBox(height: 4),
          Text(
            '${session.date} · ${session.timeRange}',
            style: TextStyle(
              fontSize: 13,
              color: isDark ? Colors.grey[400] : Colors.grey[600],
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Lieu : ${session.locationDisplay} · Type : ${session.sessionType}',
            style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.grey[500] : Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Onglet Présences ────────────────────────────────────────────────────

class _AttendanceTab extends StatefulWidget {
  final int sessionId;
  const _AttendanceTab({required this.sessionId});

  @override
  State<_AttendanceTab> createState() => _AttendanceTabState();
}

class _AttendanceTabState extends State<_AttendanceTab> {
  bool _exporting = false;

  Future<void> _exportXlsx() async {
    if (_exporting) return;
    setState(() => _exporting = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final bytes = await TeacherService().exportSessionXlsx(widget.sessionId);
      await FileShareService.shareXlsx(bytes, 'presence_${widget.sessionId}.xlsx');
    } on AppException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(content: Text('Export indisponible')),
      );
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    if (provider.sessionDetailLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    final attendees = provider.sessionAttendees;
    return RefreshIndicator(
      onRefresh: () => provider.loadSessionDetail(widget.sessionId),
      color: AppTheme.primary,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: attendees.isEmpty ? 2 : attendees.length + 1,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, i) {
          if (i == 0) {
            return OutlinedButton.icon(
              onPressed: _exporting ? null : _exportXlsx,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.primary,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              icon: _exporting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.grid_on_rounded,
                      color: AppTheme.primary),
              label: Text(_exporting
                  ? 'Génération en cours…'
                  : 'Exporter la feuille de présence (Excel)'),
            );
          }
          if (attendees.isEmpty) {
            return Card(
              elevation: 0,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 24),
                child: Column(
                  children: const [
                    Icon(Icons.people_outline_rounded,
                        size: 48, color: Colors.grey),
                    SizedBox(height: 12),
                    Text(
                      'Aucune présence enregistrée pour l\'instant',
                      style: TextStyle(color: Colors.grey),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Les étudiants scannent le QR pour être enregistrés.',
                      style:
                          TextStyle(color: Colors.grey, fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }
          final a = attendees[i - 1];
          final isDark = Theme.of(context).brightness == Brightness.dark;
          return Card(
            elevation: 0,
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: AppTheme.successColor.withOpacity(.12),
                child: const Icon(Icons.check_rounded,
                    color: AppTheme.successColor),
              ),
              title: Text(
                a.studentName.isNotEmpty
                    ? a.studentName
                    : a.studentDetail?.fullName ?? 'Étudiant',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Text(
                a.studentCodeMassar.isNotEmpty
                    ? 'Code : ${a.studentCodeMassar} · ${a.validationTime}'
                    : a.validationTime,
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.grey[400] : Colors.grey[600],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

// ─── Onglet Carte (positions GPS) ───────────────────────────────────────

class _MapTab extends StatelessWidget {
  final int sessionId;
  const _MapTab({required this.sessionId});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    final located = provider.sessionAttendees
        .where((a) => a.latitude != null && a.longitude != null)
        .toList();

    if (provider.sessionDetailLoading && located.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (located.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.location_off_rounded,
                size: 56, color: Colors.grey),
            const SizedBox(height: 12),
            const Text('Aucune position GPS enregistrée',
                style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 8),
            Text(
              'Activez la localisation lors du scan pour voir la carte.',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
      );
    }

    final markers = located
        .map((a) => Marker(
              point: LatLng(a.latitude!, a.longitude!),
              width: 44,
              height: 44,
              child: Tooltip(
                message: a.studentName.isNotEmpty
                    ? a.studentName
                    : a.studentDetail?.fullName ?? 'Étudiant',
                child: const Icon(Icons.location_on_rounded,
                    color: AppTheme.primary, size: 34),
              ),
            ))
        .toList();

    final first = located.first;
    return FlutterMap(
      options: MapOptions(
        initialCenter: LatLng(first.latitude!, first.longitude!),
        initialZoom: 16,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.attendance.app',
        ),
        MarkerLayer(markers: markers),
      ],
    );
  }
}

// ─── Onglet QR ────────────────────────────────────────────────────────────

class _QrTab extends StatefulWidget {
  final int sessionId;
  const _QrTab({required this.sessionId});

  @override
  State<_QrTab> createState() => _QrTabState();
}

class _QrTabState extends State<_QrTab> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TeacherProvider>().fetchCurrentQr(widget.sessionId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    final payload = provider.qrPayload;

    return RefreshIndicator(
      onRefresh: () => provider.fetchCurrentQr(widget.sessionId),
      color: AppTheme.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (provider.qrLoading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (payload == null || !payload.isQrValid)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Column(
                children: [
                  const Icon(Icons.qr_code_2_rounded,
                      size: 72, color: Colors.grey),
                  const SizedBox(height: 12),
                  const Text('Aucun QR actif pour cette séance',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(
                    'Générez un QR pour permettre aux étudiants de scanner.',
                    textAlign: TextAlign.center,
                    style:
                        TextStyle(color: Colors.grey[600], fontSize: 12),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => Navigator.of(context).pushNamed(
                      AppConstants.routeGenerateQr,
                      arguments: widget.sessionId,
                    ),
                    icon: const Icon(Icons.qr_code_rounded),
                    label: const Text('Générer le QR'),
                  ),
                ],
              ),
            )
          else ...[
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.primary.withOpacity(.2)),
              ),
              child: Column(
                children: [
                  if (payload.qrImageBase64 != null &&
                      payload.qrImageBase64!.isNotEmpty)
                    Image.memory(
                      _decodeBase64(payload.qrImageBase64!),
                      width: 220,
                      height: 220,
                      gaplessPlayback: true,
                    )
                  else
                    const Icon(Icons.qr_code_rounded, size: 220, color: Colors.black),
                  const SizedBox(height: 12),
                  Text(
                    'Expire le : ${payload.expiresAt?.toString() ?? '—'}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Rayon : ${payload.attendanceRadiusMeters} m',
                    style: TextStyle(
                        fontSize: 12, color: Colors.grey[600]),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => Navigator.of(context).pushNamed(
                AppConstants.routeGenerateQr,
                arguments: widget.sessionId,
              ),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Régénérer le QR'),
            ),
          ],
        ],
      ),
    );
  }

  static Uint8List _decodeBase64(String input) {
    // Supprime le préfixe data:image/png;base64,
    final comma = input.indexOf(',');
    final data = comma >= 0 ? input.substring(comma + 1) : input;
    return base64Decode(data);
  }
}

// ─── Onglet Statistiques ─────────────────────────────────────────────────

class _StatsTab extends StatelessWidget {
  final int sessionId;
  const _StatsTab({required this.sessionId});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    final stats = provider.sessionStats;

    if (provider.sessionDetailLoading && stats == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (stats == null) {
      return const Center(child: Text('Statistiques indisponibles'));
    }
    final items = [
      ('Présences', '${stats.attendanceCount}',
          Icons.event_available_rounded, AppTheme.successColor),
      ('Taux', '${stats.attendanceRate.toStringAsFixed(1)}%',
          Icons.percent_rounded, AppTheme.primary),
      ('Appareils', '${stats.uniqueDevices}', Icons.devices_rounded,
          AppTheme.accent),
      ('Doublons', '${stats.duplicateAttempts}', Icons.copy_rounded,
          AppTheme.warningColor),
      ('Hors zone', '${stats.geofenceViolations}', Icons.gps_off_rounded,
          AppTheme.errorColor),
      ('Étudiants', '${stats.totalStudentsInClass}',
          Icons.people_alt_rounded, AppTheme.primaryDark),
    ];
    return RefreshIndicator(
      onRefresh: () => provider.loadSessionDetail(sessionId),
      color: AppTheme.primary,
      child: GridView.count(
        crossAxisCount: 2,
        padding: const EdgeInsets.all(16),
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 1.4,
        physics: const AlwaysScrollableScrollPhysics(),
        children: items.map((i) {
          return Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(i.$3, color: i.$4, size: 24),
                  const SizedBox(height: 8),
                  Text(i.$2,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w700)),
                  Text(i.$1,
                      style: TextStyle(
                          fontSize: 12, color: Colors.grey[600])),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ─── Onglet Tentatives suspectes ─────────────────────────────────────────

class _SuspiciousTab extends StatelessWidget {
  final int sessionId;
  const _SuspiciousTab({required this.sessionId});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();
    if (provider.sessionDetailLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.suspiciousAttempts.isEmpty) {
      return const Center(
        child: Text('Aucune tentative suspecte',
            style: TextStyle(color: Colors.grey)),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: provider.suspiciousAttempts.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        final a = provider.suspiciousAttempts[i];
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return Card(
          elevation: 0,
          child: ListTile(
            leading: const CircleAvatar(
              backgroundColor: AppTheme.warningColor,
              child: Icon(Icons.warning_amber_rounded,
                  color: Colors.white, size: 20),
            ),
            title: Text(a.typeLabel,
                style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${a.studentName.isNotEmpty ? a.studentName : '—'}'
                  '${a.codeMassar != null ? ' · ${a.codeMassar}' : ''}',
                  style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.grey[400] : Colors.grey[600]),
                ),
                if (a.errorMessage != null && a.errorMessage!.isNotEmpty)
                  Text(
                    a.errorMessage!,
                    style: const TextStyle(fontSize: 11, color: AppTheme.errorColor),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
            isThreeLine: true,
            trailing: Text(a.createdAt.substring(0, 10),
                style: const TextStyle(fontSize: 11)),
          ),
        );
      },
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded, color: AppTheme.errorColor),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Réessayer'),
            ),
          ],
        ),
      ),
    );
  }
}
