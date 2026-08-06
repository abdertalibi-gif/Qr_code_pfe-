import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../home_screen.dart';
import 'student_schedule_screen.dart';
import 'student_stats_screen.dart';
import 'student_profile_screen.dart';

/// Écran racine de l'espace Étudiant : Bottom Navigation Bar.
///
/// Gère la synchronisation automatique de l'emploi du temps : rafraîchissement
/// périodique (timer 30 s) et rafraîchissement au retour au premier plan.
class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({super.key});

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<StudentProvider>();
      final authProvider = context.read<AuthProvider>();
      // Propagate the already-authenticated user so the WebSocket can
      // resolve the student's class ID without an extra API call.
      if ((authProvider.user?.isStudent ?? false) && provider.profile == null) {
        provider.setUserProfile(authProvider.user!);
      }
      provider.startScheduleAutoRefresh();
      if (provider.schedule.isEmpty && !provider.scheduleLoading) {
        provider.loadSchedule();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    context.read<StudentProvider>().stopScheduleAutoRefresh();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      context.read<StudentProvider>().refreshOnForeground();
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<StudentProvider>();

    final pages = [
      const HomeScreen(),
      const StudentScheduleScreen(),
      const StudentStatsScreen(),
      const StudentProfileScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: provider.currentTab.index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: provider.currentTab.index,
        onDestinationSelected: (i) => provider.setTab(StudentTab.values[i]),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Accueil',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month_rounded),
            label: 'Emploi du temps',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_outlined),
            selectedIcon: Icon(Icons.bar_chart_rounded),
            label: 'Stats',
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
