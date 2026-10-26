import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../models/session_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/teacher_provider.dart';

/// Tableau de bord enseignant : bienvenue, statistiques, séances récentes.
class TeacherDashboardScreen extends StatefulWidget {
  const TeacherDashboardScreen({super.key});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<TeacherProvider>();
      if (!provider.isLoading && provider.globalStats == null) {
        provider.loadDashboard();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final auth = context.watch<AuthProvider>();
    final provider = context.watch<TeacherProvider>();
    final stats = provider.globalStats;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tableau de bord'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<TeacherProvider>().loadDashboard(),
            tooltip: 'Actualiser',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => context.read<TeacherProvider>().loadDashboard(),
        color: AppTheme.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            _WelcomeCard(user: auth.user),
            const SizedBox(height: 16),
            if (provider.isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (provider.errorMessage != null)
              _ErrorCard(
                message: provider.errorMessage!,
                onRetry: () => context.read<TeacherProvider>().loadDashboard(),
              )
            else ...[
              _StatsGrid(stats: stats),
              const SizedBox(height: 20),
              _SectionHeader(
                title: 'Séances récentes',
                action: () => provider.setTab(TeacherTab.sessions),
              ),
              const SizedBox(height: 8),
              if (provider.recentSessions.isEmpty)
                const _EmptyCard(icon: Icons.event_note_outlined, text: 'Aucune séance récente')
              else
                ...provider.recentSessions.take(5).map(
                      (s) => _SessionCard(
                        session: s,
                        onTap: () => Navigator.of(context).pushNamed(
                          AppConstants.routeSessionDetail,
                          arguments: s.id,
                        ),
                      ),
                    ),
              const SizedBox(height: 20),
              _SectionHeader(
                title: 'Présences en direct',
                action: () => provider.setTab(TeacherTab.attendance),
              ),
              const SizedBox(height: 8),
              if (provider.liveAttendance.isEmpty)
                const _EmptyCard(
                  icon: Icons.qr_code_scanner_rounded,
                  text: 'En attente de scans…',
                )
              else
                ...provider.liveAttendance.take(8).map(
                      (a) => _LiveAttendanceCard(attendance: a),
                    ),
            ],
          ],
        ),
      ),
    );
  }
}

class _WelcomeCard extends StatelessWidget {
  final dynamic user;
  const _WelcomeCard({this.user});

  @override
  Widget build(BuildContext context) {
    final name = user != null && user!.fullName.isNotEmpty
        ? user!.fullName
        : 'Enseignant';
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppTheme.primaryGradient,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Bonjour,',
                    style: TextStyle(
                        color: Colors.white.withOpacity(.7), fontSize: 13)),
                const SizedBox(height: 4),
                Text(name,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w700),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text('Enseignant',
                      style: TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
            ),
          ),
          CircleAvatar(
            radius: 28,
            backgroundColor: Colors.white.withOpacity(.25),
            child: Text(
              user?.initials ?? '?',
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  final GlobalStats? stats;
  const _StatsGrid({this.stats});

  @override
  Widget build(BuildContext context) {
    if (stats == null) return const SizedBox.shrink();
    final s = stats!;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final brandColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;
    final items = [
      (
        Icons.event_available_rounded,
        '${s.totalPresent}',
        'Présents',
        AppTheme.successColor,
        AppTheme.successSoft,
      ),
      (
        Icons.event_busy_rounded,
        '${s.totalAbsent}',
        'Absents',
        AppTheme.errorColor,
        AppTheme.errorSoft,
      ),
      (
        Icons.percent_rounded,
        '${s.attendanceRate.toStringAsFixed(1)}%',
        'Taux',
        brandColor,
        AppTheme.primarySoft,
      ),
      (
        Icons.people_alt_rounded,
        '${s.totalStudents}',
        'Étudiants',
        AppTheme.purple,
        AppTheme.purpleSoft,
      ),
    ];
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.45,
      children: items.map((i) {
        return Card(
          elevation: 0,
          // La marge par défaut de Card (4 px de chaque côté) réduisait la
          // hauteur disponible et provoquait un débordement (« BOTTOM
          // OVERFLOWED BY 1.8 PIXELS ») sur les écrans de 320–430 px.
          margin: EdgeInsets.zero,
          color: Theme.of(context).cardTheme.color,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.radius),
            side: BorderSide(
              color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Web stat-card left colour bar.
              Container(width: 4, color: i.$4),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 30,
                        height: 30,
                        decoration: BoxDecoration(
                          color: isDark
                              ? i.$4.withOpacity(0.16)
                              : i.$5,
                          borderRadius: BorderRadius.circular(9),
                        ),
                        child: Icon(i.$1, color: i.$4, size: 17),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        i.$2,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w800),
                      ),
                      Text(
                        i.$3,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.4,
                          color: isDark
                              ? AppTheme.darkTextSecondary
                              : AppTheme.lightTextSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final VoidCallback? action;
  const _SectionHeader({required this.title, this.action});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        if (action != null)
          TextButton(
            onPressed: action,
            child: const Text('Tout voir'),
          ),
      ],
    );
  }
}

class _SessionCard extends StatelessWidget {
  final SessionModel session;
  final VoidCallback onTap;
  const _SessionCard({required this.session, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: onTap,
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: session.isActive
                ? AppTheme.successColor.withOpacity(.12)
                : AppTheme.warningColor.withOpacity(.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            session.isActive ? Icons.play_circle_rounded : Icons.check_circle_outline,
            color: session.isActive ? AppTheme.successColor : AppTheme.warningColor,
          ),
        ),
        title: Text(session.subject,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${session.classeName.isNotEmpty ? session.classeName : session.classeField} · ${session.timeRange}',
          style: TextStyle(
            fontSize: 12,
            color: isDark
                ? AppTheme.darkTextSecondary
                : AppTheme.lightTextSecondary,
          ),
        ),
        trailing: Chip(
          label: Text(session.sessionType,
              style: const TextStyle(fontSize: 11)),
          visualDensity: VisualDensity.compact,
        ),
      ),
    );
  }
}

class _LiveAttendanceCard extends StatelessWidget {
  final dynamic attendance;
  const _LiveAttendanceCard({required this.attendance});

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
        title: Text(attendance.studentName ?? attendance.subject ?? 'Présence',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${attendance.subject ?? ''} · ${attendance.sessionDate ?? ''}',
          style: TextStyle(
            fontSize: 12,
            color: isDark
                ? AppTheme.darkTextSecondary
                : AppTheme.lightTextSecondary,
          ),
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorCard({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: AppTheme.errorColor.withOpacity(.08),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Icon(Icons.cloud_off_rounded, color: AppTheme.errorColor),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 8),
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

class _EmptyCard extends StatelessWidget {
  final IconData icon;
  final String text;
  const _EmptyCard({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(
              icon,
              size: 40,
              color: isDark ? AppTheme.darkMuted : AppTheme.lightMuted,
            ),
            const SizedBox(height: 8),
            Text(
              text,
              style: TextStyle(
                color: isDark
                    ? AppTheme.darkTextSecondary
                    : AppTheme.lightTextSecondary,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
