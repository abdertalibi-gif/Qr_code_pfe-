import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/teacher_provider.dart';
import 'teacher_dashboard_screen.dart';
import 'sessions_screen.dart';
import 'teacher_attendance_screen.dart';
import 'teacher_statistics_screen.dart';
import 'teacher_profile_screen.dart';

/// Écran racine de l'espace Enseignant : Bottom Navigation Bar.
class TeacherHomeScreen extends StatefulWidget {
  const TeacherHomeScreen({super.key});

  @override
  State<TeacherHomeScreen> createState() => _TeacherHomeScreenState();
}

class _TeacherHomeScreenState extends State<TeacherHomeScreen>
    with WidgetsBindingObserver {
  Timer? _syncTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Synchronisation automatique : rafraîchit les données "live" sans repartir.
    _syncTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (!mounted) return;
      final p = context.read<TeacherProvider>();
      if (p.isDashboard || p.isAttendance || p.isStatistics) {
        p.refreshDashboardLive();
      }
    });
  }

  @override
  void dispose() {
    _syncTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Rafraîchit au retour au premier plan pour rester synchronisé.
    if (state == AppLifecycleState.resumed && mounted) {
      final p = context.read<TeacherProvider>();
      if (p.globalStats != null || !p.isLoading) {
        p.refreshDashboardLive();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TeacherProvider>();

    final pages = [
      const TeacherDashboardScreen(),
      const SessionsScreen(),
      const TeacherAttendanceScreen(),
      const TeacherStatisticsScreen(),
      const TeacherProfileScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: provider.currentTab.index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: provider.currentTab.index,
        onDestinationSelected: (i) =>
            provider.setTab(TeacherTab.values[i]),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard_rounded),
            label: 'Accueil',
          ),
          NavigationDestination(
            icon: Icon(Icons.event_note_outlined),
            selectedIcon: Icon(Icons.event_note_rounded),
            label: 'Séances',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_alt_outlined),
            selectedIcon: Icon(Icons.people_alt_rounded),
            label: 'Présences',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_outlined),
            selectedIcon: Icon(Icons.bar_chart_rounded),
            label: 'Statistiques',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded),
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}
