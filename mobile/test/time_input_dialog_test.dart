// Tests du sélecteur d'heure clavier `HH:mm` qui remplace le cadran
// circulaire de `showTimePicker` dans le formulaire « Nouvelle séance ».
//
// Couvre : formatage, analyse des saisies (avec ou sans deux-points),
// validation des bornes 00–23 / 00–59, contrainte « fin > début » et
// restitution de la valeur dans `SessionFormScreen` (payload inchangé).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:attendance_app/constants/app_theme.dart';
import 'package:attendance_app/screens/teacher/session_form_screen.dart';
import 'package:attendance_app/widgets/time_input_dialog.dart';

/// Affiche un bouton qui ouvre le dialogue et capture le résultat.
Widget _dialogHost(Future<void> Function(BuildContext) onOpen) {
  return MaterialApp(
    theme: AppTheme.lightTheme,
    home: Scaffold(
      body: Builder(
        builder: (context) => Center(
          child: ElevatedButton(
            onPressed: () => onOpen(context),
            child: const Text('Ouvrir'),
          ),
        ),
      ),
    ),
  );
}

/// Ouvre le dialogue puis saisit [input] avant de valider avec OK.
Future<void> _openAndSubmit(
  WidgetTester tester, {
  required String input,
}) async {
  await tester.tap(find.text('Ouvrir'));
  await tester.pumpAndSettle();
  await tester.enterText(find.byType(TextFormField), input);
  await tester.pump();
  await tester.tap(find.widgetWithText(ElevatedButton, 'OK'));
  await tester.pumpAndSettle();
}

void main() {
  group('formatHm', () {
    test('Formate en 24 h avec deux chiffres', () {
      expect(formatHm(const TimeOfDay(hour: 14, minute: 30)), '14:30');
      expect(formatHm(const TimeOfDay(hour: 9, minute: 5)), '09:05');
      expect(formatHm(const TimeOfDay(hour: 0, minute: 0)), '00:00');
      expect(formatHm(const TimeOfDay(hour: 23, minute: 59)), '23:59');
    });
  });

  group('parseHm — saisies valides', () {
    final valid = <String, TimeOfDay>{
      '14:30': const TimeOfDay(hour: 14, minute: 30),
      '9:30': const TimeOfDay(hour: 9, minute: 30),
      '1430': const TimeOfDay(hour: 14, minute: 30),
      '930': const TimeOfDay(hour: 9, minute: 30),
      '14h30': const TimeOfDay(hour: 14, minute: 30),
      '14:30:00': const TimeOfDay(hour: 14, minute: 30),
      '9:5': const TimeOfDay(hour: 9, minute: 5),
      ' 14:30 ': const TimeOfDay(hour: 14, minute: 30),
      '00:00': const TimeOfDay(hour: 0, minute: 0),
      '23:59': const TimeOfDay(hour: 23, minute: 59),
    };

    valid.forEach((input, expected) {
      test('« $input » → ${formatHm(expected)}', () {
        final parsed = parseHm(input);
        expect(parsed, isNotNull);
        expect(formatHm(parsed!), formatHm(expected));
      });
    });
  });

  group('parseHm — saisies invalides', () {
    const invalid = [
      '',
      '   ',
      '24:00',
      '23:60',
      '14:60',
      '25:00',
      '14:',
      ':30',
      'abcd',
      '12345',
    ];

    for (final input in invalid) {
      test('« $input » est refusé', () {
        expect(parseHm(input), isNull);
      });
    }
  });

  testWidgets('Saisir 14:30 puis OK renvoie l\'heure choisie', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 8, minute: 0),
      );
    }));

    // Le champ affiche une valeur d'exemple et sélectionne l'existant.
    await tester.tap(find.text('Ouvrir'));
    await tester.pumpAndSettle();
    expect(find.text('Heure de début'), findsOneWidget);
    expect(find.text('08:00'), findsOneWidget);
    expect(find.text('14:30'), findsOneWidget); // hint

    await tester.enterText(find.byType(TextFormField), '14:30');
    await tester.pump();
    await tester.tap(find.widgetWithText(ElevatedButton, 'OK'));
    await tester.pumpAndSettle();

    expect(result, isNotNull);
    expect(formatHm(result!), '14:30');
  });

  testWidgets('La saisie compacte 1430 devient 14:30', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de fin',
        initialTime: const TimeOfDay(hour: 16, minute: 0),
      );
    }));

    await _openAndSubmit(
      tester,
      input: '1430',
    );

    expect(result, isNotNull);
    expect(formatHm(result!), '14:30');
  });

  testWidgets('La saisie 930 devient 09:30', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 8, minute: 0),
      );
    }));

    await _openAndSubmit(
      tester,
      input: '930',
    );

    expect(result, isNotNull);
    expect(formatHm(result!), '09:30');
  });

  testWidgets('24:00 est refusé et le dialogue reste ouvert', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 14, minute: 0),
      );
    }));

    await _openAndSubmit(
      tester,
      input: '24:00',
    );

    expect(result, isNull);
    expect(find.text('Heure de début'), findsOneWidget);
    expect(
      find.text('Heure invalide. Saisissez HH:mm entre 00:00 et 23:59.'),
      findsOneWidget,
    );
  });

  testWidgets('14:60 est refusé (minutes hors bornes)', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 14, minute: 0),
      );
    }));

    await _openAndSubmit(
      tester,
      input: '14:60',
    );

    expect(result, isNull);
    expect(
      find.text('Heure invalide. Saisissez HH:mm entre 00:00 et 23:59.'),
      findsOneWidget,
    );
  });

  testWidgets('Un champ vide est refusé', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 14, minute: 0),
      );
    }));

    await _openAndSubmit(
      tester,
      input: '',
    );

    expect(result, isNull);
    expect(
      find.text('Heure invalide. Saisissez HH:mm entre 00:00 et 23:59.'),
      findsOneWidget,
    );
  });

  testWidgets('La fin doit être postérieure au début', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de fin',
        initialTime: const TimeOfDay(hour: 16, minute: 0),
        mustBeAfter: const TimeOfDay(hour: 14, minute: 0),
      );
    }));

    // 14:00 est refusé (égalité).
    await _openAndSubmit(
      tester,
      input: '14:00',
    );
    expect(result, isNull);
    expect(
      find.text("L'heure de fin doit être après l'heure de début (14:00)."),
      findsOneWidget,
    );

    // 14:01 est accepté.
    await tester.enterText(find.byType(TextFormField), '14:01');
    await tester.pump();
    await tester.tap(find.widgetWithText(ElevatedButton, 'OK'));
    await tester.pumpAndSettle();

    expect(result, isNotNull);
    expect(formatHm(result!), '14:01');
  });

  testWidgets('Annuler ne renvoie aucune valeur', (tester) async {
    TimeOfDay? result;

    await tester.pumpWidget(_dialogHost((context) async {
      result = await showTimeInputDialog(
        context,
        title: 'Heure de début',
        initialTime: const TimeOfDay(hour: 14, minute: 0),
      );
    }));

    await tester.tap(find.text('Ouvrir'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField), '15:00');
    await tester.tap(find.widgetWithText(TextButton, 'Annuler'));
    await tester.pumpAndSettle();

    expect(result, isNull);
    expect(find.byType(TextFormField), findsNothing);
  });

  testWidgets(
    'SessionFormScreen : taper 14:30 dans Début l\'affiche dans le formulaire',
    (tester) async {
      SharedPreferences.setMockInitialValues({});

      tester.view.physicalSize = const Size(390, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const SessionFormScreen(),
        ),
      );
      // Laisse les chargements réseau échouer (400 en environnement de test).
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));

      expect(find.text('Début'), findsOneWidget);
      expect(find.text('14:00'), findsOneWidget);

      await tester.tap(find.text('Début'));
      await tester.pumpAndSettle();

      expect(find.text('Heure de début'), findsOneWidget);
      await tester.enterText(find.byType(TextFormField), '14:30');
      await tester.pump();
      await tester.tap(find.widgetWithText(ElevatedButton, 'OK'));
      await tester.pumpAndSettle();

      // Le dialogue est fermé et l'heure normalisée est affichée.
      expect(find.text('Heure de début'), findsNothing);
      expect(find.text('14:30'), findsOneWidget);
    },
  );
}
