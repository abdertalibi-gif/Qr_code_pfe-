import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../models/attendance_model.dart';
import '../../providers/student_provider.dart';

/// Emploi du temps + Modules + Historique des présences.
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
      if (provider.schedule.isEmpty && !provider.isLoading) {
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

// ─── Onglet Cours / Modules ───────────────────────────────────────────────

class _ScheduleTab extends StatelessWidget {
  final StudentProvider provider;
  const _ScheduleTab({required this.provider});

  @override
  Widget build(BuildContext context) {
    if (provider.isLoading && provider.schedule.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.schedule.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => provider.loadSchedule(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 80),
            Icon(Icons.calendar_month_outlined,
                size: 56, color: Colors.grey),
            SizedBox(height: 12),
            Center(
              child: Text('Aucun cours planifié pour le moment',
                  style: TextStyle(color: Colors.grey)),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () => provider.loadSchedule(),
      color: AppTheme.primary,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: provider.schedule.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) {
          final c = provider.schedule[i];
          final isDark = Theme.of(context).brightness == Brightness.dark;
          return Card(
            elevation: 0,
            child: ListTile(
              leading: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppTheme.primary.withOpacity(.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.menu_book_rounded,
                    color: AppTheme.primary),
              ),
              title: Text(c.moduleName ?? c.name,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(
                [
                  if (c.filiereName != null) c.filiereName!,
                  if (c.semestreName != null) c.semestreName!,
                ].join(' · '),
                style: TextStyle(
                    fontSize: 12,
                    color: isDark ? Colors.grey[400] : Colors.grey[600]),
              ),
              trailing: Chip(
                label: Text(c.name,
                    style: const TextStyle(fontSize: 10)),
                visualDensity: VisualDensity.compact,
              ),
            ),
          );
        },
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
    if (provider.historyLoading && provider.attendanceHistory.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.attendanceHistory.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => provider.loadHistory(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 80),
            Icon(Icons.event_note_outlined, size: 56, color: Colors.grey),
            SizedBox(height: 12),
            Center(
              child: Text('Aucune présence enregistrée',
                  style: TextStyle(color: Colors.grey)),
            ),
            SizedBox(height: 4),
            Center(
              child: Text(
                'Scannez un QR en cours pour commencer.',
                style: TextStyle(color: Colors.grey, fontSize: 12),
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
        separatorBuilder: (_, __) => const SizedBox(height: 8),
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
              color: isDark ? Colors.grey[400] : Colors.grey[600]),
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
