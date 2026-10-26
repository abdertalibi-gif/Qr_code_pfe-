import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../models/session_model.dart';
import '../../providers/teacher_provider.dart';

/// Liste des classes et séances de l'enseignant.
class SessionsScreen extends StatefulWidget {
  const SessionsScreen({super.key});

  @override
  State<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends State<SessionsScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  Future<void> _openForm({SessionModel? session}) async {
    await Navigator.of(context).pushNamed(
      AppConstants.routeSessionForm,
      arguments: session,
    );
    if (mounted) context.read<TeacherProvider>().refreshSessions();
  }

  Future<void> _openDetail(int id) async {
    await Navigator.of(context).pushNamed(
      AppConstants.routeSessionDetail,
      arguments: id,
    );
    if (mounted) context.read<TeacherProvider>().refreshSessions();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<TeacherProvider>();
      if (provider.classes.isEmpty && !provider.sessionsLoading) {
        provider.loadSessions();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final provider = context.watch<TeacherProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes séances'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_rounded),
            tooltip: 'Nouvelle séance',
            onPressed: () => _openForm(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => provider.loadSessions(),
        color: AppTheme.primary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            if (provider.sessionsLoading && provider.classes.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (provider.sessionsError != null && provider.classes.isEmpty)
              _ErrorState(
                message: provider.sessionsError!,
                onRetry: () => provider.loadSessions(),
              )
            else if (provider.classes.isEmpty)
              const _EmptyState()
            else ...[
              // ── Sélecteur de classe ───────────────────────────────────
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: provider.classes.map((c) {
                    final selected = provider.selectedClasse?.id == c.id;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: ConstrainedBox(
                          constraints: BoxConstraints(
                            maxWidth:
                                MediaQuery.of(context).size.width * 0.72,
                          ),
                          child: Text(
                            c.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        selected: selected,
                        onSelected: (_) => provider.selectClasse(c),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 16),
              if (provider.sessionsLoading)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (provider.sessions.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(32),
                  child: Center(
                    child: Text(
                      'Aucune séance pour cette classe',
                      style: TextStyle(
                        color: Theme.of(context).textTheme.bodyMedium?.color,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              else
                ...provider.sessions.map(
                  (s) => _SessionTile(
                    session: s,
                    onTap: () => _openDetail(s.id),
                    onEdit: () => _openForm(session: s),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SessionTile extends StatelessWidget {
  final SessionModel session;
  final VoidCallback onTap;
  final VoidCallback onEdit;
  const _SessionTile({
    required this.session,
    required this.onTap,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final now = DateTime.now();
    final inWindow = session.isWithinSessionWindow;
    final isPast = (session.dateTimeEnd ?? DateTime(2000)).isBefore(now);

    /// « 20:14:57 » -> « 20:14 » : évite que l'horaire soit tronqué sur les
    /// petits écrans (320–430 px).
    String short(String value) {
      final parts = value.split(':');
      return parts.length >= 2 ? '${parts[0]}:${parts[1]}' : value;
    }

    final timeRange =
        '${short(session.startTime)}–${short(session.endTime)}';
    final muted = isDark ? AppTheme.darkMuted : AppTheme.lightMuted;
    final brandColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: session.isActive && inWindow
                      ? AppTheme.successColor.withOpacity(.12)
                      : isPast
                          ? muted.withOpacity(.15)
                          : AppTheme.warningColor.withOpacity(.12),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(
                  session.isActive && inWindow
                      ? Icons.play_circle_rounded
                      : isPast
                          ? Icons.done_all_rounded
                          : Icons.schedule_rounded,
                  color: session.isActive && inWindow
                      ? AppTheme.successColor
                      : isPast
                          ? muted
                          : AppTheme.warningColor,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      session.subject,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: brandColor.withOpacity(isDark ? .18 : .10),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            session.sessionType,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: brandColor,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '${session.date} · $timeRange',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              color: isDark
                                  ? AppTheme.darkTextSecondary
                                  : AppTheme.lightTextSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.edit_outlined, size: 20),
                onPressed: onEdit,
                tooltip: 'Modifier',
                visualDensity: VisualDensity.compact,
                constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        children: [
          Icon(
            Icons.school_outlined,
            size: 56,
            color: isDark ? AppTheme.darkMuted : AppTheme.lightMuted,
          ),
          const SizedBox(height: 12),
          const Text('Aucune classe assignée',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(
            'Contactez l\'administration pour vous assigner des classes.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isDark
                  ? AppTheme.darkTextSecondary
                  : AppTheme.lightTextSecondary,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
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
    );
  }
}
