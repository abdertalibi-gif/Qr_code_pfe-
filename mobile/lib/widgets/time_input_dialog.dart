import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Formate une heure au format 24 h `HH:mm` (identique au `<input type="time">`
/// du formulaire Web).
String formatHm(TimeOfDay time) {
  final h = time.hour.toString().padLeft(2, '0');
  final m = time.minute.toString().padLeft(2, '0');
  return '$h:$m';
}

/// Analyse une heure saisie au clavier.
///
/// Formats acceptés : `14:30`, `9:30`, `1430`, `930`, `14h30` ou `14:30:00`.
/// Retourne `null` si l'heure ou les minutes sont hors bornes
/// (heures 00–23, minutes 00–59).
TimeOfDay? parseHm(String input) {
  var value = input.trim().toLowerCase().replaceAll('h', ':');
  value = value.replaceAll(' ', '');

  final withSeparator =
      RegExp(r'^(\d{1,2}):(\d{1,2})(?::\d{1,2})?$').firstMatch(value);
  if (withSeparator != null) {
    return _buildTime(withSeparator.group(1)!, withSeparator.group(2)!);
  }

  // Saisie compacte sans séparateur : 930 ou 1430.
  final compact = RegExp(r'^\d{3,4}$').firstMatch(value);
  if (compact != null) {
    final digits = compact.group(0)!;
    final hour = digits.length == 3
        ? digits.substring(0, 1)
        : digits.substring(0, 2);
    final minute = digits.substring(digits.length - 2);
    return _buildTime(hour, minute);
  }

  return null;
}

TimeOfDay? _buildTime(String hourText, String minuteText) {
  final hour = int.tryParse(hourText);
  final minute = int.tryParse(minuteText);
  if (hour == null || minute == null) return null;
  if (hour < 0 || hour > 23) return null;
  if (minute < 0 || minute > 59) return null;
  return TimeOfDay(hour: hour, minute: minute);
}

/// Ouvre une boîte de dialogue de saisie directe de l'heure.
///
/// Remplace le cadran circulaire de `showTimePicker` par un champ texte
/// `HH:mm` validé, avec un exemple `14:30`, aux couleurs du formulaire Web.
Future<TimeOfDay?> showTimeInputDialog(
  BuildContext context, {
  required String title,
  required TimeOfDay initialTime,
  TimeOfDay? mustBeAfter,
  String confirmLabel = 'OK',
}) {
  return showDialog<TimeOfDay>(
    context: context,
    builder: (_) => _TimeInputDialog(
      title: title,
      initialTime: initialTime,
      mustBeAfter: mustBeAfter,
      confirmLabel: confirmLabel,
    ),
  );
}

class _TimeInputDialog extends StatefulWidget {
  final String title;
  final TimeOfDay initialTime;
  final TimeOfDay? mustBeAfter;
  final String confirmLabel;

  const _TimeInputDialog({
    required this.title,
    required this.initialTime,
    required this.mustBeAfter,
    required this.confirmLabel,
  });

  @override
  State<_TimeInputDialog> createState() => _TimeInputDialogState();
}

class _TimeInputDialogState extends State<_TimeInputDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: formatHm(widget.initialTime));
    // Sélectionne l'heure existante : taper directement remplace la valeur.
    _controller.selection = TextSelection(
      baseOffset: 0,
      extentOffset: _controller.text.length,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String? _validate(String? value) {
    final parsed = parseHm(value ?? '');
    if (parsed == null) {
      return 'Heure invalide. Saisissez HH:mm entre 00:00 et 23:59.';
    }
    final minimum = widget.mustBeAfter;
    if (minimum != null && _minutes(parsed) <= _minutes(minimum)) {
      return "L'heure de fin doit être après l'heure de début "
          '(${formatHm(minimum)}).';
    }
    return null;
  }

  int _minutes(TimeOfDay time) => time.hour * 60 + time.minute;

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final parsed = parseHm(_controller.text);
    if (parsed == null) return;
    Navigator.of(context).pop(parsed);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: Form(
        key: _formKey,
        child: TextFormField(
          controller: _controller,
          autofocus: true,
          keyboardType: TextInputType.datetime,
          textInputAction: TextInputAction.done,
          textAlign: TextAlign.center,
          maxLength: 5,
          autovalidateMode: AutovalidateMode.disabled,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9:]')),
            const _HmInputFormatter(),
          ],
          style: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
          ),
          decoration: const InputDecoration(
            labelText: 'Heure (HH:mm)',
            hintText: '14:30',
            helperText: 'Exemple : 14:30 — heures 00–23, minutes 00–59',
            counterText: '',
            prefixIcon: Icon(Icons.schedule_rounded),
          ),
          validator: _validate,
          onFieldSubmitted: (_) => _submit(),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Annuler'),
        ),
        ElevatedButton(
          onPressed: _submit,
          style: ElevatedButton.styleFrom(
            minimumSize: const Size(88, 44),
          ),
          child: Text(widget.confirmLabel),
        ),
      ],
    );
  }
}

/// Insère automatiquement les deux-points : `1430` devient `14:30`.
class _HmInputFormatter extends TextInputFormatter {
  const _HmInputFormatter();

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final raw = newValue.text;
    final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');

    String text;
    if (raw.contains(':')) {
      // L'utilisateur a saisi les deux-points lui-même : on respecte sa saisie.
      text = raw;
    } else if (digits.length <= 2) {
      text = digits;
    } else if (digits.length == 3) {
      // Heure à deux chiffres si elle est valide (143 -> 14:3),
      // sinon heure à un chiffre (930 -> 9:30).
      final twoDigitHour = int.tryParse(digits.substring(0, 2)) ?? 99;
      text = twoDigitHour <= 23
          ? '${digits.substring(0, 2)}:${digits.substring(2)}'
          : '${digits.substring(0, 1)}:${digits.substring(1)}';
    } else {
      // 1430 (ou saisie progressive 1, 14, 143, 1430) -> 14:30
      text = '${digits.substring(0, 2)}:${digits.substring(2, 4)}';
    }

    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }
}
