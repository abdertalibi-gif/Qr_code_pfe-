// Test de base : vérifie que l'application démarre sans erreur.

import 'package:flutter_test/flutter_test.dart';

import 'package:attendance_app/main.dart';

void main() {
  testWidgets('App builds without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const AttendanceApp());
    await tester.pump(const Duration(seconds: 1));
    expect(find.byType(AttendanceApp), findsOneWidget);
  });
}
