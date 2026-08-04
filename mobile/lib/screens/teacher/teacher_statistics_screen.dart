import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../providers/teacher_provider.dart';

/// Statistiques globales de l'enseignant.
class TeacherStatisticsScreen extends StatefulWidget {
  const TeacherStatisticsScreen({super.key});

  @override
  State<TeacherStatisticsScreen> createState() =>
      _TeacherStatisticsScreenState();
}

class _TeacherStatisticsScreenState extends State<TeacherStatisticsScreen>
    with AutomaticKeepAliveClientMixin {
  int _period = 30;

  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final provider = context.watch<TeacherProvider>();
    final stats = provider.globalStats;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Statistiques'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => provider.loadDashboard(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => provider.loadDashboard(),
        color: AppTheme.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            // ── Période ────────────────────────────────────────────────
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 7, label: Text('7 j')),
                ButtonSegment(value: 30, label: Text('30 j')),
                ButtonSegment(value: 90, label: Text('90 j')),
              ],
              selected: {_period},
              onSelectionChanged: (v) {
                setState(() => _period = v.first);
                context.read<TeacherProvider>().loadGlobalStats(v.first);
              },
            ),
            const SizedBox(height: 16),

            if (provider.isLoading && stats == null)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (stats == null)
              Center(
                child: TextButton.icon(
                  onPressed: () => provider.loadDashboard(),
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Charger les statistiques'),
                ),
              )
            else ...[
              _StatCard(
                icon: Icons.event_available_rounded,
                color: AppTheme.successColor,
                label: 'Présences',
                value: '${stats.totalPresent}',
              ),
              const SizedBox(height: 10),
              _StatCard(
                icon: Icons.event_busy_rounded,
                color: AppTheme.errorColor,
                label: 'Absences',
                value: '${stats.totalAbsent}',
              ),
              const SizedBox(height: 10),
              _StatCard(
                icon: Icons.percent_rounded,
                color: AppTheme.primary,
                label: 'Taux de présence',
                value: '${stats.attendanceRate.toStringAsFixed(1)}%',
              ),
              const SizedBox(height: 10),
              _StatCard(
                icon: Icons.people_alt_rounded,
                color: AppTheme.primaryDark,
                label: 'Étudiants',
                value: '${stats.totalStudents}',
              ),
              const SizedBox(height: 20),
              Text('Activité des derniers jours',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              if (stats.daily.isEmpty)
                Text('Aucune donnée quotidienne',
                    style: TextStyle(
                        color: isDark ? Colors.grey[500] : Colors.grey[600]))
              else
                ...stats.daily.take(14).map((d) {
                  final pct = d.total == 0
                      ? 0.0
                      : (d.present / d.total).clamp(0.0, 1.0);
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(d.date,
                                style: const TextStyle(fontSize: 12)),
                            Text('${d.present}/${d.total}',
                                style: const TextStyle(fontSize: 12)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: LinearProgressIndicator(
                            value: pct,
                            minHeight: 6,
                            backgroundColor:
                                isDark ? Colors.white12 : Colors.black12,
                            color: AppTheme.successColor,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final String value;

  const _StatCard({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: ListTile(
        leading: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: color.withOpacity(.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color),
        ),
        title: Text(value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
        subtitle: Text(label),
      ),
    );
  }
}
