// Test de non-débordement : tous les écrans s'affichent sans RenderFlex
// Overflow sur les largeurs de téléphone courantes (320, 360, 375, 390, 430).
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

/// Largeurs logiques testées (px) : petits Android, iPhone SE, iPhone 13/14,
/// Pixel et grands iPhone Pro Max.
const List<double> _phoneWidths = [320, 360, 375, 390, 430];

/// Hauteur logique représentative d'un téléphone en portrait.
const double _phoneHeight = 800;

Map<String, Widget> _screens() => <String, Widget>{
      'HomeScreen': const HomeScreen(),
      'LoginScreen': const LoginScreen(),
      'ValidationScreen': const ValidationScreen(),
      'ErrorScreen': const ErrorScreen(),
      'SuccessScreen': const SuccessScreen(),
      'RoleNotSupportedScreen': const RoleNotSupportedScreen(),
      'StudentScheduleScreen': const StudentScheduleScreen(),
      'StudentStatsScreen': const StudentStatsScreen(),
      'StudentProfileScreen': const StudentProfileScreen(),
      'TeacherDashboardScreen': const TeacherDashboardScreen(),
      'SessionsScreen': const SessionsScreen(),
      'TeacherAttendanceScreen': const TeacherAttendanceScreen(),
      'TeacherStatisticsScreen': const TeacherStatisticsScreen(),
      'TeacherProfileScreen': const TeacherProfileScreen(),
      'SessionFormScreen': const SessionFormScreen(),
      'GenerateQrScreen': const GenerateQrScreen(sessionId: 1),
      'SessionDetailScreen': const SessionDetailScreen(sessionId: 1),
    };

Widget _app(Widget screen, ThemeData theme) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<ThemeProvider>(create: (_) => ThemeProvider()),
      ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
      ChangeNotifierProvider<AttendanceProvider>(
          create: (_) => AttendanceProvider()),
      ChangeNotifierProvider<TeacherProvider>(create: (_) => TeacherProvider()),
      ChangeNotifierProvider<StudentProvider>(create: (_) => StudentProvider()),
    ],
    child: MaterialApp(
      theme: theme,
      home: screen,
    ),
  );
}

Future<void> _pumpScreen(
  WidgetTester tester,
  Widget screen,
  ThemeData theme,
) async {
  await tester.pumpWidget(_app(screen, theme));
  await tester.pump(const Duration(seconds: 1));
  await tester.pump(const Duration(seconds: 1));
  await tester.pump(const Duration(seconds: 1));
}

void main() {
  for (final width in _phoneWidths) {
    testWidgets(
      'Tous les écrans s\'affichent sans overflow sur ${width.toInt()}x'
      '${_phoneHeight.toInt()}',
      (WidgetTester tester) async {
        tester.view.physicalSize = Size(width, _phoneHeight);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.reset);

        for (final entry in _screens().entries) {
          final overflowErrors = <String>[];
          final oldHandler = FlutterError.onError;
          FlutterError.onError = (FlutterErrorDetails details) {
            if (details.toString().contains('RenderFlex overflowed')) {
              overflowErrors.add(details.toString());
            }
          };

          await _pumpScreen(tester, entry.value, AppTheme.lightTheme);

          FlutterError.onError = oldHandler;

          expect(
            overflowErrors,
            isEmpty,
            reason: 'Overflow détecté sur ${entry.key} en ${width.toInt()} px',
          );
        }
      },
    );
  }

  testWidgets(
    'Les écrans principaux s\'affichent sans overflow en thème sombre '
    '(390x800)',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(390, _phoneHeight);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      for (final entry in _screens().entries) {
        final overflowErrors = <String>[];
        final oldHandler = FlutterError.onError;
        FlutterError.onError = (FlutterErrorDetails details) {
          if (details.toString().contains('RenderFlex overflowed')) {
            overflowErrors.add(details.toString());
          }
        };

        await _pumpScreen(tester, entry.value, AppTheme.darkTheme);

        FlutterError.onError = oldHandler;

        expect(
          overflowErrors,
          isEmpty,
          reason: 'Overflow détecté sur ${entry.key} (thème sombre)',
        );
      }
    },
  );
}
