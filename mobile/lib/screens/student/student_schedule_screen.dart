import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../models/attendance_model.dart';
import '../../models/student_schedule_model.dart';
import '../../providers/student_provider.dart';

/// Emploi du temps dynamique + Historique des présences.
class StudentScheduleScreen extends StatefulWidget {
  const StudentScheduleScreen({super.key});

  @override
  State<StudentScheduleScreen> createState() => _StudentScheduleScreenState();
}

class _StudentScheduleScreenState extends State<StudentScheduleScreen>
    with AutomaticKeepAliveClientMixin, SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<StudentProvider>();
      if (provider.schedule.isEmpty && !provider.scheduleLoading) {
        provider.loadSchedule();
      }
      if (provider.attendanceHistory.isEmpty && !provider.historyLoading) {
        provider.loadHistory();
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final provider = context.watch<StudentProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Emploi du temps'),
        actions: [
          if (provider.wsConnected)
            Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.successColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.circle, size: 8, color: AppTheme.successColor),
                  SizedBox(width: 4),
                  Text('En direct',
                      style: TextStyle(
                          fontSize: 11,
                          color: AppTheme.successColor,
                          fontWeight: FontWeight.w600)),
                ],
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              provider.loadSchedule();
              provider.loadHistory();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: 'Cours'),
              Tab(text: 'Présences'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _ScheduleTab(provider: provider),
                _HistoryTab(provider: provider),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Onglet Emploi du temps ───────────────────────────────────────────────

class _ScheduleTab extends StatelessWidget {
  final StudentProvider provider;
  const _ScheduleTab({required this.provider});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    if (provider.scheduleLoading && provider.schedule.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.scheduleError != null && provider.schedule.isEmpty) {
      return _ErrorState(
        message: provider.scheduleError!,
        onRetry: () => provider.loadSchedule(),
      );
    }
    if (provider.schedule.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => provider.loadSchedule(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 80),
            Icon(Icons.calendar_month_outlined, size: 56, color: muted),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Aucune séance planifiée pour le moment',
                style: TextStyle(color: muted, fontSize: 14),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      );
    }

    final days = _groupByDay(provider.schedule);

    return RefreshIndicator(
      onRefresh: () => provider.loadSchedule(),
      color: AppTheme.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (provider.lastScheduleSync != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (provider.wsConnected)
                    const Padding(
                      padding: EdgeInsets.only(right: 6),
                      child: Icon(Icons.circle, size: 8, color: AppTheme.successColor),
                    ),
                  Flexible(
                    child: Text(
                      'Synchronisé à '
                      '${_formatTime(provider.lastScheduleSync!)} · '
                      '${provider.wsConnected ? 'en temps réel' : 'rafraîchi automatiquement'}',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 11,
                        color: secondaryColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ...days.entries.map(
            (entry) => _DaySection(dayLabel: entry.key, items: entry.value),
          ),
        ],
      ),
    );
  }

  static Map<String, List<StudentScheduleItem>> _groupByDay(
    List<StudentScheduleItem> items,
  ) {
    final grouped = <String, List<StudentScheduleItem>>{};
    for (final item in items) {
      grouped.putIfAbsent(item.date, () => []).add(item);
    }
    final orderedKeys = grouped.keys.toList()
      ..sort((a, b) => a.compareTo(b));
    return {for (final k in orderedKeys) k: grouped[k]!};
  }

  static String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

// ─── Section d'un jour ────────────────────────────────────────────────────

class _DaySection extends StatelessWidget {
  final String dayLabel;
  final List<StudentScheduleItem> items;

  const _DaySection({required this.dayLabel, required this.items});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final date = DateTime.tryParse(dayLabel);
    final isToday = _isToday(date);
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;

    final sorted = [...items]..sort((a, b) => a.startMinutes - b.startMinutes);

    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: isToday
                        ? (isDark ? AppTheme.primaryOnDark : AppTheme.primary)
                        : (isDark
                            ? AppTheme.primary.withOpacity(0.16)
                            : AppTheme.primarySoft),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _dayName(dayLabel, date),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: isToday
                          ? Colors.white
                          : (isDark ? AppTheme.darkTextPrimary : AppTheme.primary),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    _formatDate(dayLabel, date),
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: secondaryColor,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          ...sorted.map((item) => _SessionCard(item: item)),
        ],
      ),
    );
  }

  static bool _isToday(DateTime? date) {
    if (date == null) return false;
    final now = DateTime.now();
    return date.year == now.year &&
        date.month == now.month &&
        date.day == now.day;
  }

  static String _dayName(String iso, DateTime? date) {
    if (date == null) return iso;
    const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
    return days[date.weekday - 1];
  }

  static String _formatDate(String iso, DateTime? date) {
    if (date == null) return iso;
    const months = [
      'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
      'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }
}

// ─── Carte séance ─────────────────────────────────────────────────────────

class _SessionCard extends StatelessWidget {
  final StudentScheduleItem item;
  const _SessionCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isOngoing = item.status == ScheduleStatus.ongoing;
    final isCancelled = item.status == ScheduleStatus.cancelled;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final brandColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;

    final statusColor = switch (item.status) {
      ScheduleStatus.upcoming => brandColor,
      ScheduleStatus.ongoing => AppTheme.successColor,
      ScheduleStatus.finished => muted,
      ScheduleStatus.cancelled => AppTheme.errorColor,
    };

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        border: Border.all(
          color: isOngoing ? AppTheme.successColor : borderColor,
          width: isOngoing ? 1.5 : 1,
        ),
        boxShadow: isOngoing
            ? [
                BoxShadow(
                  color: AppTheme.successColor.withOpacity(.18),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Créneau horaire vertical.
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.startTime,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: brandColor,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  item.endTime,
                  style: TextStyle(
                    fontSize: 12,
                    color: secondaryColor,
                  ),
                ),
              ],
            ),
            const SizedBox(width: 12),
            Container(
              width: 4,
              height: 52,
              decoration: BoxDecoration(
                color: isCancelled ? AppTheme.errorColor : statusColor,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          item.title,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: isDark
                                ? AppTheme.darkTextPrimary
                                : AppTheme.lightTextPrimary,
                            decoration:
                                isCancelled ? TextDecoration.lineThrough : null,
                            decorationColor: AppTheme.errorColor,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      _TypeBadge(type: item.sessionTypeLabel),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _InfoRow(
                    icon: Icons.person_outline_rounded,
                    text: item.teacherName.isEmpty ? '—' : item.teacherName,
                  ),
                  const SizedBox(height: 4),
                  _InfoRow(
                    icon: Icons.place_outlined,
                    text: item.locationDisplay,
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _StatusChip(status: item.status),
                      if (item.qrOpen) const _QrOpenBadge(),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TypeBadge extends StatelessWidget {
  final String type;
  const _TypeBadge({required this.type});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: isDark
            ? AppTheme.primary.withOpacity(0.18)
            : AppTheme.primaryLight,
        borderRadius: BorderRadius.circular(8),
      ),
      constraints: const BoxConstraints(maxWidth: 96),
      child: Text(
        type,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final iconColor = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    final textColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    return Row(
      children: [
        Icon(icon, size: 14, color: iconColor),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 12.5,
              color: textColor,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _StatusChip extends StatelessWidget {
  final ScheduleStatus status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final color = switch (status) {
      ScheduleStatus.upcoming =>
        isDark ? AppTheme.primaryOnDark : AppTheme.primary,
      ScheduleStatus.ongoing => AppTheme.successColor,
      ScheduleStatus.finished =>
        isDark ? AppTheme.darkMuted : AppTheme.lightMuted,
      ScheduleStatus.cancelled => AppTheme.errorColor,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == ScheduleStatus.ongoing) ...[
            const SizedBox(
              width: 8,
              height: 8,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.successColor),
            ),
            const SizedBox(width: 6),
          ],
          Text(
            status.label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _QrOpenBadge extends StatelessWidget {
  const _QrOpenBadge();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final brandColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: brandColor.withOpacity(isDark ? .2 : .12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.qr_code_2_rounded, size: 14, color: brandColor),
          const SizedBox(width: 6),
          Text(
            'Présence ouverte',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: brandColor,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Onglet Historique des présences ──────────────────────────────────────

class _HistoryTab extends StatelessWidget {
  final StudentProvider provider;
  const _HistoryTab({required this.provider});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    if (provider.historyLoading && provider.attendanceHistory.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.historyError != null && provider.attendanceHistory.isEmpty) {
      return _ErrorState(
        message: provider.historyError!,
        onRetry: () => provider.loadHistory(),
      );
    }
    if (provider.attendanceHistory.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => provider.loadHistory(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 80),
            Icon(Icons.event_note_outlined, size: 56, color: muted),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Aucune présence enregistrée',
                style: TextStyle(color: muted, fontSize: 14),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 4),
            Center(
              child: Text(
                'Scannez un QR en cours pour commencer.',
                style: TextStyle(color: muted, fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () => provider.loadHistory(),
      color: AppTheme.primary,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: provider.attendanceHistory.length,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, i) =>
            _HistoryCard(attendance: provider.attendanceHistory[i]),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  final AttendanceModel attendance;
  const _HistoryCard({required this.attendance});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      elevation: 0,
      child: ListTile(
        leading: const CircleAvatar(
          backgroundColor: AppTheme.successColor,
          child: Icon(Icons.check_rounded, color: Colors.white),
        ),
        title: Text(
          attendance.studentDetail?.fullName ?? 'Présence',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          attendance.formattedValidationTime,
          style: TextStyle(
            fontSize: 12,
            color: isDark
                ? AppTheme.darkTextSecondary
                : AppTheme.lightTextSecondary,
          ),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: AppTheme.successColor.withOpacity(.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Text('Présent',
              style: TextStyle(
                  fontSize: 11,
                  color: AppTheme.successColor,
                  fontWeight: FontWeight.w600)),
        ),
      ),
    );
  }
}

// ─── État d'erreur partagé ───────────────────────────────────────────────

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    return RefreshIndicator(
      onRefresh: () async => onRetry(),
      color: AppTheme.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 80),
          Icon(Icons.cloud_off_outlined, size: 56, color: muted),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: muted, fontSize: 13),
            ),
          ),
          const SizedBox(height: 12),
          Center(
            child: TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Réessayer'),
            ),
          ),
        ],
      ),
    );
  }
}
