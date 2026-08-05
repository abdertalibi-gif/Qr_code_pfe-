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
                        label: Text(
                          c.name,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
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
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(
                    child: Text('Aucune séance pour cette classe',
                        style: TextStyle(color: Colors.grey)),
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

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: onTap,
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: session.isActive && inWindow
                ? AppTheme.successColor.withOpacity(.12)
                : isPast
                    ? Colors.grey.withOpacity(.15)
                    : AppTheme.warningColor.withOpacity(.12),
            borderRadius: BorderRadius.circular(12),
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
                    ? Colors.grey
                    : AppTheme.warningColor,
          ),
        ),
        title: Text(session.subject,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${session.date} · ${session.timeRange}',
          style: TextStyle(fontSize: 12, color: isDark ? Colors.grey[400] : Colors.grey[600]),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Chip(
              label: Text(session.sessionType,
                  style: const TextStyle(fontSize: 10)),
              visualDensity: VisualDensity.compact,
            ),
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20),
              onPressed: onEdit,
              tooltip: 'Modifier',
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        children: [
          Icon(Icons.school_outlined, size: 56, color: Colors.grey[400]),
          const SizedBox(height: 12),
          const Text('Aucune classe assignée',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(
            'Contactez l\'administration pour vous assigner des classes.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
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
