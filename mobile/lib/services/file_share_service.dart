import 'dart:io';
import 'dart:typed_data';

import 'package:share_plus/share_plus.dart';

/// Sauvegarde un fichier temporaire et ouvre le panneau de partage Android.
class FileShareService {
  static const String _xlsxMime =
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

  /// Écrit [bytes] dans un fichier temporaire puis ouvre le share sheet.
  static Future<void> shareXlsx(Uint8List bytes, String filename) async {
    final dir = await Directory.systemTemp.createTemp('attendance_export_');
    final file = File('${dir.path}${Platform.pathSeparator}$filename');
    await file.writeAsBytes(bytes, flush: true);
    await Share.shareXFiles(
      [XFile(file.path, mimeType: _xlsxMime)],
      subject: filename,
    );
  }
}
