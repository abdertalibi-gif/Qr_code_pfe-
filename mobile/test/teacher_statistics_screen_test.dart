// Régression : les cartes de statistiques utilisaient un Row avec
// CrossAxisAlignment.stretch dans une ListView (hauteur non bornée), ce qui
// provoquait « BoxConstraints forces an infinite height ». Le correctif
// enveloppe le Row dans un IntrinsicHeight ; ce test vérifie que les cartes
// se rendent correctement en clair comme en sombre.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:attendance_app/constants/app_theme.dart';
import 'package:attendance_app/models/classe_model.dart';
import 'package:attendance_app/models/session_model.dart';
import 'package:attendance_app/providers/teacher_provider.dart';
import 'package:attendance_app/screens/teacher/teacher_statistics_screen.dart';
import 'package:attendance_app/services/teacher_service.dart';

class _FakeTeacherService extends TeacherService {
  @override
  Future<List<ClasseModel>> fetchClasses() async => const [];

  @override
  Future<List<SessionModel>> fetchSessions({int? classeId}) async => const [];

  @override
  Future<List<SessionAttendance>> fetchLiveAttendance() async => const [];

  @override
  Future<GlobalStats> fetchGlobalStats({int period = 30}) async {
    return const GlobalStats(
      totalPresent: 2,
      totalAttendance: 5,
      attendanceRate: 40,
      totalStudents: 1,
      daily: [DailyAttendance(date: '2026-10-28', present: 1, total: 1)],
    );
  }
}

Future<TeacherProvider> _loadedProvider() async {
  final provider = TeacherProvider(teacherService: _FakeTeacherService());
  await provider.loadDashboard();
  return provider;
}

void main() {
  for (final brightness in [Brightness.light, Brightness.dark]) {
    testWidgets('TeacherStatisticsScreen rend les cartes sans hauteur infinie '
        '(${brightness.name})', (tester) async {
      tester.view.physicalSize = const Size(360, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final provider = await _loadedProvider();

      await tester.pumpWidget(
        ChangeNotifierProvider<TeacherProvider>.value(
          value: provider,
          child: MaterialApp(
            theme: brightness == Brightness.dark
                ? AppTheme.darkTheme
                : AppTheme.lightTheme,
            home: const TeacherStatisticsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('PRÉSENCES'), findsOneWidget);
      expect(find.text('ABSENCES'), findsOneWidget);
      expect(find.text('TAUX DE PRÉSENCE'), findsOneWidget);
      expect(find.text('ÉTUDIANTS'), findsOneWidget);
      expect(find.text('Activité des derniers jours'), findsOneWidget);
      expect(find.text('1/1'), findsOneWidget);
    });
  }
}
