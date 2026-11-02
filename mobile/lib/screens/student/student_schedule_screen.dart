import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../models/attendance_model.dart';
import '../../models/student_schedule_model.dart';
import '../../models/user_model.dart';
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
          if (provider.profile?.studentProfile != null)
            _ClassInfoBanner(profile: provider.profile!.studentProfile!),
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
    final profile = provider.profile?.studentProfile;

    if (provider.scheduleLoading && provider.schedule.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.scheduleError != null && provider.schedule.isEmpty) {
      return _ErrorState(
        message: provider.scheduleError!,
        onRetry: () => provider.loadSchedule(),
      );
    }

    // Grouper les séances par classe_id
    final sessionsByClass = <int?, List<StudentScheduleItem>>{};
    for (final item in provider.schedule) {
      sessionsByClass.putIfAbsent(item.classe, () => []).add(item);
    }
    // Trier chaque groupe par date/heure
    sessionsByClass.forEach((_, items) {
      items.sort((a, b) {
        final da = a.date.compareTo(b.date);
        if (da != 0) return da;
        return a.startMinutes.compareTo(b.startMinutes);
      });
    });

    // Classe de l'étudiant (depuis le profil)
    final studentClasseId = profile?.classeId;
    final studentClasseName = profile?.classeName;

    // Construire la liste des classes à afficher : d'abord celle de l'étudiant,
    // puis les autres classes qui ont des séances
    final displayClasses = <MapEntry<int?, Map<String, dynamic>>>[];
    if (studentClasseId != null) {
      displayClasses.add(MapEntry(
        studentClasseId,
        {
          'name': studentClasseName ?? 'Classe',
          'filiere': profile?.filiereName ?? '—',
          'semestre': profile?.semestreName ?? '—',
          'niveau': profile?.niveau ?? '—',
          'academicYear': profile?.academicYear ?? '—',
          'modules': profile?.modules ?? const [],
        },
      ));
    }
    sessionsByClass.forEach((cid, items) {
      if (cid != null && cid != studentClasseId) {
        // Utiliser les infos de la première séance pour cette classe
        final first = items.first;
        displayClasses.add(MapEntry(
          cid,
          {
            'name': first.classeName.isNotEmpty ? first.classeName : 'Classe #$cid',
            'filiere': first.filiereName.isNotEmpty ? first.filiereName : '—',
            'semestre': first.semestreName.isNotEmpty ? first.semestreName : '—',
            'niveau': first.niveauLabel.isNotEmpty ? first.niveauLabel : '—',
            'academicYear': '—',
            'modules': const <StudentModule>[],
          },
        ));
      }
    });

    if (displayClasses.isEmpty && provider.schedule.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => provider.loadSchedule(),
        color: AppTheme.primary,
        child: _EmptySchedule(
          classeName: studentClasseName,
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => provider.loadSchedule(),
      color: AppTheme.primary,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          // ── Statut de synchronisation ───────────────────────────────
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

          // ── Classes avec leurs séances ─────────────────────────────
          ...displayClasses.map((entry) {
            final classeId = entry.key;
            final info = entry.value;
            final sessions = sessionsByClass[classeId] ?? const <StudentScheduleItem>[];
            return _ClassSessionCard(
              classeId: classeId,
              classeName: info['name'] as String,
              filiereName: info['filiere'] as String,
              semestreName: info['semestre'] as String,
              niveau: info['niveau'] as String,
              academicYear: info['academicYear'] as String,
              modules: info['modules'] as List<StudentModule>,
              sessions: sessions,
            );
          }).toList(),
        ],
      ),
    );
  }
}

// ─── Carte de classe avec ses séances à l'intérieur ─────────────────

class _ClassSessionCard extends StatelessWidget {
  final int? classeId;
  final String classeName;
  final String filiereName;
  final String semestreName;
  final String niveau;
  final String academicYear;
  final List<StudentModule> modules;
  final List<StudentScheduleItem> sessions;

  const _ClassSessionCard({
    required this.classeId,
    required this.classeName,
    required this.filiereName,
    required this.semestreName,
    required this.niveau,
    required this.academicYear,
    required this.modules,
    required this.sessions,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary = isDark ? AppTheme.darkTextSecondary : AppTheme.lightMuted;
    final hasSessions = sessions.isNotEmpty;
    final details = [
      filiereName,
      semestreName,
      academicYear,
    ].where((v) => v != null && v.isNotEmpty && v != '—').cast<String>().join(' · ');

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // En-tête de la classe
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: isDark
                      ? AppTheme.primary.withOpacity(.15)
                      : AppTheme.primaryLight,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  Icons.school_rounded,
                  size: 18,
                  color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      classeName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: isDark
                            ? AppTheme.darkTextPrimary
                            : AppTheme.lightTextPrimary,
                      ),
                    ),
                    if (details.isNotEmpty)
                      Text(
                        details,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: secondary),
                      ),
                    if (modules.isNotEmpty)
                      Text(
                        '${modules.length} module${modules.length > 1 ? 's' : ''}',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.primary,
                        ),
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: hasSessions
                      ? AppTheme.successColor.withOpacity(.12)
                      : AppTheme.lightMuted.withOpacity(.3),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  hasSessions
                      ? '${sessions.length} séance${sessions.length > 1 ? 's' : ''}'
                      : 'Aucune séance',
                  style: TextStyle(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    color: hasSessions
                        ? AppTheme.successColor
                        : secondary,
                  ),
                ),
              ),
            ],
          ),

          // Niveau et année
          if (niveau.isNotEmpty && niveau != '—') ...[
            const SizedBox(height: 8),
            Row(
              children: [
                _InfoChip(icon: Icons.stairs_outlined, label: niveau),
                if (academicYear.isNotEmpty && academicYear != '—')
                  _InfoChip(icon: Icons.today, label: academicYear),
              ],
            ),
          ],

          // Séances de la classe
          if (hasSessions) ...[
            const SizedBox(height: 10),
            Text(
              'Séances',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: secondary,
              ),
            ),
            const SizedBox(height: 6),
            ...sessions.map((session) => _MiniSessionRow(session: session)),
          ] else ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: isDark
                    ? AppTheme.darkCard.withOpacity(.3)
                    : AppTheme.lightCard.withOpacity(.3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.event_busy,
                    size: 20,
                    color: secondary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Aucune séance programmée pour cette classe.',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: secondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Petite puce d'information
class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: isDark
            ? AppTheme.darkCard.withOpacity(.6)
            : Colors.white.withOpacity(.8),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: AppTheme.primary),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w600,
              color: isDark ? AppTheme.darkTextPrimary : AppTheme.primaryDark,
            ),
          ),
        ],
      ),
    ),
  }
}

/// Petite ligne de séance à l'intérieur d'une carte de classe
class _MiniSessionRow extends StatelessWidget {
  final StudentScheduleItem session;
  const _MiniSessionRow({required this.session});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isOngoing = session.status == ScheduleStatus.ongoing;
    final isCancelled = session.status == ScheduleStatus.cancelled;
    final secondaryColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightMuted;

    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isOngoing
              ? AppTheme.successColor
              : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
          width: isOngoing ? 1.5 : 1,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Horaire
          Container(
            width: 72,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  session.startTime,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: isOngoing
                        ? AppTheme.successColor
                        : (isDark
                            ? AppTheme.darkTextPrimary
                            : AppTheme.lightTextPrimary),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  session.endTime,
                  style: TextStyle(
                    fontSize: 10,
                    color: secondaryColor,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          // Ligne verticale
          Container(
            width: 3,
            height: 44,
            decoration: BoxDecoration(
              color: isOngoing
                  ? AppTheme.successColor
                  : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 8),
          // Contenu
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        session.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: isCancelled
                              ? secondaryColor
                              : (isDark
                                  ? AppTheme.darkTextPrimary
                                  : AppTheme.lightTextPrimary),
                          decoration: isCancelled
                              ? TextDecoration.lineThrough
                              : null,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    _SessionTypeBadge(type: session.sessionTypeLabel),
                  ],
                ),
                const SizedBox(height: 6),
                _MiniInfoRow(icon: Icons.person_outline_rounded, text: session.teacherName.isEmpty ? '—' : session.teacherName),
                const SizedBox(height: 3),
                _MiniInfoRow(icon: Icons.place_outlined, text: session.locationDisplay),
                const SizedBox(height: 3),
                _MiniInfoRow(icon: Icons.calendar_today, text: session.date),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _SessionStatusChip(status: session.status),
                    if (session.qrOpen) const _QrOpenBadgeMini(),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Badge de type de séance (mini)
class _SessionTypeBadge extends StatelessWidget {
  final String type;
  const _SessionTypeBadge({required this.type});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: isDark
            ? AppTheme.primary.withOpacity(0.18)
            : AppTheme.primaryLight,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        type,
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w700,
          color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

/// Mini ligne d'information
class _MiniInfoRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _MiniInfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final iconColor = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    final textColor =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    return Row(
      children: [
        Icon(icon, size: 12, color: iconColor),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 11,
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

/// Puce de statut (mini)
class _SessionStatusChip extends StatelessWidget {
  final ScheduleStatus status;
  const _SessionStatusChip({required this.status});

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
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == ScheduleStatus.ongoing) ...[
            const SizedBox(
              width: 7,
              height: 7,
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: AppTheme.successColor),
            ),
            const SizedBox(width: 5),
          ],
          Text(
            status.label,
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

/// Badge QR ouvert (mini)
class _QrOpenBadgeMini extends StatelessWidget {
  const _QrOpenBadgeMini();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final brandColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: brandColor.withOpacity(isDark ? .2 : .12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.qr_code_2_rounded, size: 12, color: brandColor),
          const SizedBox(width: 5),
          Text(
            'Présence ouverte',
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
              color: brandColor,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── État vide de l'emploi du temps ────────────────────────────────────

class _EmptySchedule extends StatelessWidget {
  final String? classeName;

  const _EmptySchedule({
    required this.classeName,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 40),
            Icon(Icons.calendar_month_outlined, size: 56, color: muted),
            const SizedBox(height: 12),
            Text(
              classeName != null && classeName.isNotEmpty
                  ? 'Aucune séance planifiée pour $classeName'
                  : 'Aucune classe ne vous est affectée',
              style: TextStyle(color: muted, fontSize: 14),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
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

/// Bandeau « Ma classe » : affiche la classe réellement affectée à l'étudiant.
/// Les données proviennent de `/auth/me/` (rafraîchi toutes les 30 s).
/// Même sans aucune séance créée, la classe et les modules inscrits apparaissent.
class _ClassInfoBanner extends StatelessWidget {
  final StudentProfile profile;
  const _ClassInfoBanner({required this.profile});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    final details = [
      profile.filiereName,
      profile.semestreName,
      profile.academicYear,
    ].where((value) => value != null && value.isNotEmpty).cast<String>().join(' · ');

    if (profile.classeName == null || profile.classeName!.isEmpty) {
      return const SizedBox.shrink();
    }

    final modules = profile.modules;

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  AppTheme.primary.withOpacity(.22),
                  AppTheme.primary.withOpacity(.08),
                ]
              : [
                  AppTheme.primarySoft,
                  AppTheme.primaryLight,
                ],
        ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark
              ? AppTheme.primary.withOpacity(.35)
              : AppTheme.primaryBorder,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : Colors.white,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: isDark
                        ? AppTheme.primary.withOpacity(.35)
                        : AppTheme.primaryBorder,
                  ),
                ),
                child: Icon(
                  Icons.school_rounded,
                  size: 20,
                  color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      profile.classeName!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        color: isDark
                            ? AppTheme.darkTextPrimary
                            : AppTheme.lightTextPrimary,
                      ),
                    ),
                    if (details.isNotEmpty)
                      Text(
                        details,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: secondary),
                      ),
                  ],
                ),
              ),
              if (modules.isNotEmpty)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: isDark
                        ? AppTheme.primary.withOpacity(.26)
                        : Colors.white,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${modules.length} module${modules.length > 1 ? 's' : ''}',
                    style: TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                    ),
                  ),
                ),
            ],
          ),
          if (modules.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: modules
                  .map(
                    (module) => Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(
                        color: isDark
                            ? AppTheme.darkCard.withOpacity(.65)
                            : Colors.white.withOpacity(.85),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: isDark
                              ? AppTheme.darkBorder
                              : AppTheme.primaryBorder,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            module.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 10.5,
                              fontWeight: FontWeight.w700,
                              color: isDark
                                  ? AppTheme.darkTextPrimary
                                  : AppTheme.primaryDark,
                            ),
                          ),
                          if (module.code.isNotEmpty)
                            Text(
                              module.code,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 8.5,
                                fontWeight: FontWeight.w600,
                                color: isDark
                                    ? AppTheme.darkMuted
                                    : AppTheme.lightMuted,
                              ),
                            ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (modules.isEmpty) ...[
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.only(left: 4),
              child: Text(
                'Aucun module inscrit',
                style: TextStyle(
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                  color: secondary,
                ),
              ),
            ),
          ],
        ],
      ),
    );
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
                  const SizedBox(height: 4),
                  _InfoRow(
                    icon: Icons.class_outlined,
                    text: item.classeName.isEmpty ? '—' : item.classeName,
                  ),
                  const SizedBox(height: 4),
                  _InfoRow(
                    icon: Icons.school_outlined,
                    text: item.academicLabel,
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
