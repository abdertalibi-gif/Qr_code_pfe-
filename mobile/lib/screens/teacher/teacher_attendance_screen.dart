import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_theme.dart';
import '../../providers/teacher_provider.dart';

/// Présences en direct : flux des scans récents.
class TeacherAttendanceScreen extends StatefulWidget {
  const TeacherAttendanceScreen({super.key});

  @override
  State<TeacherAttendanceScreen> createState() =>
      _TeacherAttendanceScreenState();
}

class _TeacherAttendanceScreenState extends State<TeacherAttendanceScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<TeacherProvider>();
      if (provider.liveAttendance.isEmpty && !provider.isLoading) {
        provider.loadDashboard();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final provider = context.watch<TeacherProvider>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Présences en direct'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => provider.loadDashboard(),
            tooltip: 'Actualiser',
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
            if (provider.isLoading && provider.liveAttendance.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (provider.liveAttendance.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Column(
                  children: [
                    Icon(Icons.radar_rounded,
                        size: 56, color: Colors.grey[400]),
                    const SizedBox(height: 12),
                    const Text('Aucun scan pour l\'instant',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(
                      'Les présences apparaissent ici en temps réel '
                      'lorsque les étudiants scannent le QR.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: Colors.grey[600], fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...provider.liveAttendance.map((a) {
                return Card(
                  elevation: 0,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: AppTheme.successColor,
                      child: Icon(Icons.check_rounded,
                          color: Colors.white),
                    ),
                    title: Text(
                      a.studentName.isNotEmpty
                          ? a.studentName
                          : a.studentDetail?.fullName ?? 'Étudiant',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${a.studentCodeMassar.isNotEmpty ? '${a.studentCodeMassar} · ' : ''}'
                      '${a.subject.isNotEmpty ? '${a.subject} · ' : ''}'
                      '${a.sessionDate.isNotEmpty ? a.sessionDate : ''}',
                      style: TextStyle(
                        fontSize: 12,
                        color: isDark ? Colors.grey[400] : Colors.grey[600],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: Text(
                      a.validationTime.substring(11, 16),
                      style: TextStyle(
                          fontSize: 11,
                          color: isDark ? Colors.grey[500] : Colors.grey[500]),
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}
