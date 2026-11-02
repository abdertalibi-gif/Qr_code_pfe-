import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../models/student_schedule_model.dart';
import '../../models/user_model.dart';
import '../../providers/student_provider.dart';

/// Écran d'emploi du temps + Historique des présences avec consultation par module.
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
                  Text(
                    'En direct',
                    style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.successColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          IconButton(
            tooltip: 'Actualiser',
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

// ─── Onglet Emploi du temps (Cours) ──────────────────────────────────────────

class _ScheduleTab extends StatelessWidget {
  final StudentProvider provider;
  const _ScheduleTab({required this.provider});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightMuted;
    final profile = provider.profile?.studentProfile;
    final isModuleFiltered = provider.selectedModuleId != null;

    if (provider.scheduleLoading && provider.schedule.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.scheduleError != null && provider.schedule.isEmpty) {
      return _ErrorState(
        message: provider.scheduleError!,
        onRetry: () => provider.loadSchedule(),
      );
    }

    final modules = profile?.modules ?? <StudentModule>[];

    // Grouper les modules par semestre (S1, S2, S3, S4, S5, S6)
    final modulesBySemester = <String, List<StudentModule>>{};
    for (final module in modules) {
      final sem = module.semestreName.isNotEmpty ? module.semestreName : 'Autres';
      modulesBySemester.putIfAbsent(sem, () => []).add(module);
    }

    final sortedSemestres = modulesBySemester.keys.toList()
      ..sort((a, b) {
        final numA = int.tryParse(a.replaceAll(RegExp(r'\D'), '')) ?? 99;
        final numB = int.tryParse(b.replaceAll(RegExp(r'\D'), '')) ?? 99;
        return numA.compareTo(numB);
      });

    return RefreshIndicator(
      onRefresh: () => provider.loadSchedule(),
      color: AppTheme.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          // ── Synchronisation / statut ─────────────────────────────────────
          if (provider.lastScheduleSync != null && !isModuleFiltered)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
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
                      '${provider.wsConnected ? 'en temps réel' : 'rafraîchi'}',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 11, color: secondaryColor),
                    ),
                  ),
                ],
              ),
            ),

          // ── Barre de filtre actif (si module sélectionné) ───────────────
          if (isModuleFiltered)
            _ActiveModuleFilterBanner(
              moduleName: provider.selectedModuleName ?? 'Module sélectionné',
              semestreName: provider.selectedModuleSemestre ?? '',
              onReset: () => provider.clearModuleFilter(),
            ),

          // ── Section « Vos classes et modules » (si aucun filtre actif) ──
          if (!isModuleFiltered && sortedSemestres.isNotEmpty) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                borderRadius: BorderRadius.circular(AppTheme.radius),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_stories_outlined,
                          size: 18, color: AppTheme.primary),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Vos classes et modules',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Touchez un module pour afficher uniquement ses séances',
                    style: TextStyle(
                      fontSize: 11,
                      color: secondaryColor,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Divider(height: 1),
                  const SizedBox(height: 10),
                  ...sortedSemestres.map((semestre) {
                    final semModules = modulesBySemester[semestre]!;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2.5),
                            decoration: BoxDecoration(
                              color: AppTheme.primary.withOpacity(isDark ? .2 : .1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: AppTheme.primary.withOpacity(0.25),
                              ),
                            ),
                            child: Text(
                              semestre,
                              style: const TextStyle(
                                fontSize: 10.5,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.primary,
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 8,
                            runSpacing: 6,
                            children: semModules.map((m) {
                              return _ModuleButton(
                                module: m,
                                isDark: isDark,
                                onTap: () {
                                  provider.filterByModule(
                                    m.id,
                                    m.name,
                                    m.semestreName,
                                  );
                                },
                              );
                            }).toList(),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
            Row(
              children: [
                Icon(Icons.calendar_month_outlined,
                    size: 16, color: AppTheme.primary),
                const SizedBox(width: 6),
                const Text(
                  'Toutes les séances',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: isDark ? AppTheme.darkDivider : AppTheme.lightDivider,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${provider.schedule.length}',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: secondaryColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
          ],

          // ── Liste des séances ───────────────────────────────────────────
          if (provider.schedule.isEmpty)
            _EmptyState(
              message: isModuleFiltered
                  ? "Aucune séance n'est programmée pour ce module."
                  : 'Aucune séance prévue pour votre classe.',
              actionLabel: isModuleFiltered ? 'Retour aux modules' : 'Actualiser',
              onAction: isModuleFiltered
                  ? () => provider.clearModuleFilter()
                  : () => provider.loadSchedule(),
            )
          else
            ...provider.schedule.map((session) => _SessionCard(
                  session: session,
                  isDark: isDark,
                )),
        ],
      ),
    );
  }
}

// ─── Bannière de filtre de module actif ──────────────────────────────────────

class _ActiveModuleFilterBanner extends StatelessWidget {
  final String moduleName;
  final String semestreName;
  final VoidCallback onReset;

  const _ActiveModuleFilterBanner({
    required this.moduleName,
    required this.semestreName,
    required this.onReset,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0A4368), Color(0xFF0F6E9F)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppTheme.radius),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0A4368).withOpacity(0.35),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text(
                  'MODULE SÉLECTIONNÉ',
                  style: TextStyle(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                    color: Colors.white,
                  ),
                ),
              ),
              if (semestreName.isNotEmpty) ...[
                const SizedBox(width: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF28C28).withOpacity(0.85),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    semestreName,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Text(
            moduleName,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: ElevatedButton.icon(
              onPressed: onReset,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: const Color(0xFF0A4368),
                elevation: 0,
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              icon: const Icon(Icons.arrow_back_rounded, size: 16),
              label: const Text(
                'Retour aux modules',
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Bouton module cliquable ─────────────────────────────────────────────────

class _ModuleButton extends StatelessWidget {
  final StudentModule module;
  final bool isDark;
  final VoidCallback onTap;

  const _ModuleButton({
    required this.module,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final initial =
        module.name.isNotEmpty ? module.name[0].toUpperCase() : '?';

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.darkCard : const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: AppTheme.primary.withOpacity(0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Center(
                child: Text(
                  initial,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 7),
            Flexible(
              child: Text(
                module.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Carte Séance (SessionCard) ──────────────────────────────────────────────

class _SessionCard extends StatelessWidget {
  final StudentScheduleItem session;
  final bool isDark;

  const _SessionCard({required this.session, required this.isDark});

  Color _statusColor(ScheduleStatus status) {
    switch (status) {
      case ScheduleStatus.ongoing:
        return const Color(0xFF10B981);
      case ScheduleStatus.cancelled:
        return AppTheme.errorColor;
      case ScheduleStatus.finished:
        return const Color(0xFF64748B);
      case ScheduleStatus.upcoming:
        return AppTheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor(session.status);
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightMuted;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        border: Border.all(
          color: session.status == ScheduleStatus.ongoing
              ? const Color(0xFF10B981).withOpacity(0.4)
              : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
          width: session.status == ScheduleStatus.ongoing ? 1.5 : 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.2 : 0.03),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Titre et Statut
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  session.title,
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w800,
                    decoration: session.status == ScheduleStatus.cancelled
                        ? TextDecoration.lineThrough
                        : null,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: statusColor.withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (session.status == ScheduleStatus.ongoing) ...[
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: statusColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 4),
                    ],
                    Text(
                      session.status.label,
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w700,
                        color: statusColor,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Enseignant
          Row(
            children: [
              Icon(Icons.person_outline_rounded,
                  size: 15, color: secondaryColor),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  session.teacherName.isNotEmpty
                      ? session.teacherName
                      : 'Enseignant non assigné',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: isDark
                        ? AppTheme.darkTextPrimary
                        : AppTheme.lightTextPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),

          // Date et Horaires (Début & Fin)
          Row(
            children: [
              Icon(Icons.access_time_rounded,
                  size: 15, color: secondaryColor),
              const SizedBox(width: 6),
              Text(
                '${_formatTimeStr(session.startTime)} – ${_formatTimeStr(session.endTime)}',
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (session.date.isNotEmpty) ...[
                const SizedBox(width: 12),
                Icon(Icons.calendar_today_outlined,
                    size: 14, color: secondaryColor),
                const SizedBox(width: 5),
                Text(
                  session.date,
                  style: TextStyle(
                    fontSize: 12,
                    color: secondaryColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),

          // Lieu, Type et Présence ouverte
          Wrap(
            spacing: 8,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              // Type (Cours / TD / TP)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkDivider : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  session.sessionTypeLabel,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: isDark
                        ? AppTheme.darkTextSecondary
                        : AppTheme.lightTextSecondary,
                  ),
                ),
              ),

              // Lieu
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.location_on_outlined,
                      size: 14, color: secondaryColor),
                  const SizedBox(width: 3),
                  Text(
                    session.locationDisplay,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: secondaryColor,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),

              // Classe
              if (session.classeName.isNotEmpty)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.school_outlined,
                        size: 14, color: secondaryColor),
                    const SizedBox(width: 3),
                    Text(
                      session.classeName,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: secondaryColor,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),

              // Badge QR Ouvert
              if (session.qrOpen)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.qr_code_rounded,
                          size: 12, color: Color(0xFF10B981)),
                      SizedBox(width: 4),
                      Text(
                        'Présence ouverte',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF10B981),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  static String _formatTimeStr(String time) {
    if (time.length >= 5) return time.substring(0, 5);
    return time.isEmpty ? '—' : time;
  }
}

// ─── Onglet Présences (HistoryTab) ───────────────────────────────────────────

class _HistoryTab extends StatelessWidget {
  final StudentProvider provider;
  const _HistoryTab({required this.provider});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightMuted;

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
      return _EmptyState(
        message: 'Aucune présence enregistrée.',
        actionLabel: 'Actualiser',
        onAction: () => provider.loadHistory(),
      );
    }

    return RefreshIndicator(
      onRefresh: () => provider.loadHistory(),
      color: AppTheme.primary,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        itemCount: provider.attendanceHistory.length,
        itemBuilder: (context, index) {
          final record = provider.attendanceHistory[index];
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
              borderRadius: BorderRadius.circular(AppTheme.radius),
              border: Border.all(
                color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Center(
                    child: Icon(Icons.check_circle_outline_rounded,
                        color: Color(0xFF10B981), size: 20),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Séance #${record.session}',
                        style: const TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        record.validationTime.length >= 16
                            ? record.validationTime.substring(0, 16).replaceAll('T', ' à ')
                            : record.validationTime,
                        style: TextStyle(
                          fontSize: 11.5,
                          color: secondaryColor,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text(
                    'Présent',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF10B981),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ─── États vides et erreurs ──────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const _EmptyState({
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_busy_rounded, size: 52, color: muted),
            const SizedBox(height: 12),
            Text(
              message,
              style: TextStyle(color: muted, fontSize: 13.5),
              textAlign: TextAlign.center,
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: onAction,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                icon: const Icon(Icons.refresh_rounded, size: 16),
                label: Text(
                  actionLabel!,
                  style: const TextStyle(fontSize: 12.5),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const _ErrorState({required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline_rounded,
                size: 52, color: AppTheme.errorColor),
            const SizedBox(height: 12),
            Text(
              message,
              style: const TextStyle(fontSize: 13.5),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded, size: 16),
                label: const Text('Réessayer'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _formatTime(DateTime dateTime) {
  return '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
