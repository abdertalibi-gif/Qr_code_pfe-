import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../models/attendance_model.dart';
import '../../providers/student_provider.dart';

/// Statistiques personnelles de l'étudiant.
class StudentStatsScreen extends StatefulWidget {
  const StudentStatsScreen({super.key});

  @override
  State<StudentStatsScreen> createState() => _StudentStatsScreenState();
}

class _StudentStatsScreenState extends State<StudentStatsScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<StudentProvider>();
      if (provider.attendanceHistory.isEmpty && !provider.historyLoading) {
        provider.loadHistory();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final provider = context.watch<StudentProvider>();
    final history = provider.attendanceHistory;

    // Calcul local des statistiques depuis l'historique
    final total = history.length;
    final present = history
        .where((a) => a.attendanceStatus != 'absent')
        .length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistiques personnelles'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => provider.loadHistory(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => provider.loadHistory(),
        color: AppTheme.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            if (provider.historyLoading && history.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (history.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Column(
                  children: [
                    Icon(Icons.insights_outlined,
                        size: 56, color: Colors.grey[400]),
                    const SizedBox(height: 12),
                    const Text('Aucune donnée disponible',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(
                      'Scannez des QR pour générer vos statistiques.',
                      style:
                          TextStyle(color: Colors.grey[600], fontSize: 12),
                    ),
                  ],
                ),
              )
            else ...[
              // ── Taux global ──────────────────────────────────────────
              _RateCard(total: total, present: present),
              const SizedBox(height: 20),
              Text('Détail par séance',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              ...history.take(20).map(
                    (a) => _HistoryDetailCard(attendance: a),
                  ),
            ],
          ],
        ),
      ),
    );
  }
}

class _RateCard extends StatelessWidget {
  final int total;
  final int present;
  const _RateCard({required this.total, required this.present});

  @override
  Widget build(BuildContext context) {
    final rate = total == 0 ? 0.0 : present / total;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primary, AppTheme.primaryDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        children: [
          Text(
            '${(rate * 100).toStringAsFixed(1)}%',
            style: const TextStyle(
                color: Colors.white,
                fontSize: 36,
                fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          const Text('Taux de présence',
              style: TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _MiniStat(label: 'Présences', value: '$present'),
              _MiniStat(label: 'Total séances', value: '$total'),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: rate,
              minHeight: 8,
              backgroundColor: Colors.white.withOpacity(.2),
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String label;
  final String value;
  const _MiniStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w700)),
        Text(label,
            style: const TextStyle(color: Colors.white70, fontSize: 11)),
      ],
    );
  }
}

class _HistoryDetailCard extends StatelessWidget {
  final AttendanceModel attendance;
  const _HistoryDetailCard({required this.attendance});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: const CircleAvatar(
          backgroundColor: AppTheme.successColor,
          child: Icon(Icons.check_rounded, color: Colors.white),
        ),
        title: Text(
          attendance.studentDetail?.fullName ?? 'Présence',
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        ),
        subtitle: Text(
          attendance.formattedValidationTime,
          style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.grey[400] : Colors.grey[600]),
        ),
      ),
    );
  }
}
