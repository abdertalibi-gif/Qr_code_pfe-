// Test de non-débordement : tous les écrans s'affichent sans RenderFlex
// Overflow sur une résolution Android étroite (360x800).
//
// Les services HTTP échouent volontairement en environnement de test
// (flutter_test renvoie 400 pour toute requête) : les écrans doivent donc
// afficher leur état d'erreur SANS overflow ni exception non gérée.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:attendance_app/constants/app_theme.dart';
import 'package:attendance_app/providers/attendance_provider.dart';
import 'package:attendance_app/providers/auth_provider.dart';
import 'package:attendance_app/providers/student_provider.dart';
import 'package:attendance_app/providers/teacher_provider.dart';
import 'package:attendance_app/providers/theme_provider.dart';
import 'package:attendance_app/screens/error_screen.dart';
import 'package:attendance_app/screens/home_screen.dart';
import 'package:attendance_app/screens/login_screen.dart';
import 'package:attendance_app/screens/role_not_supported_screen.dart';
import 'package:attendance_app/screens/success_screen.dart';
import 'package:attendance_app/screens/validation_screen.dart';
import 'package:attendance_app/screens/student/student_profile_screen.dart';
import 'package:attendance_app/screens/student/student_schedule_screen.dart';
import 'package:attendance_app/screens/student/student_stats_screen.dart';
import 'package:attendance_app/screens/teacher/generate_qr_screen.dart';
import 'package:attendance_app/screens/teacher/session_detail_screen.dart';
import 'package:attendance_app/screens/teacher/session_form_screen.dart';
import 'package:attendance_app/screens/teacher/sessions_screen.dart';
import 'package:attendance_app/screens/teacher/teacher_attendance_screen.dart';
import 'package:attendance_app/screens/teacher/teacher_dashboard_screen.dart';
import 'package:attendance_app/screens/teacher/teacher_profile_screen.dart';
import 'package:attendance_app/screens/teacher/teacher_statistics_screen.dart';

void main() {
  testWidgets('Tous les écrans s\'affichent sans overflow sur 360x800',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final screens = <Widget>[
      const HomeScreen(),
      const LoginScreen(),
      const ValidationScreen(),
      const ErrorScreen(),
      const SuccessScreen(),
      const RoleNotSupportedScreen(),
      const StudentScheduleScreen(),
      const StudentStatsScreen(),
      const StudentProfileScreen(),
      const TeacherDashboardScreen(),
      const SessionsScreen(),
      const TeacherAttendanceScreen(),
      const TeacherStatisticsScreen(),
      const TeacherProfileScreen(),
      const SessionFormScreen(),
      const GenerateQrScreen(sessionId: 1),
      const SessionDetailScreen(sessionId: 1),
    ];

    for (final screen in screens) {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<ThemeProvider>(
              create: (_) => ThemeProvider(),
            ),
            ChangeNotifierProvider<AuthProvider>(
              create: (_) => AuthProvider(),
            ),
            ChangeNotifierProvider<AttendanceProvider>(
              create: (_) => AttendanceProvider(),
            ),
            ChangeNotifierProvider<TeacherProvider>(
              create: (_) => TeacherProvider(),
            ),
            ChangeNotifierProvider<StudentProvider>(
              create: (_) => StudentProvider(),
            ),
          ],
          child: MaterialApp(
            theme: AppTheme.lightTheme,
            home: screen,
          ),
        ),
      );
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));

      expect(
        tester.takeException(),
        isNull,
        reason: 'Exception ou overflow détecté sur : $screen',
      );
    }
  });
}
