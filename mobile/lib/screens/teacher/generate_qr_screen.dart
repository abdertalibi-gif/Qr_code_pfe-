import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../constants/app_theme.dart';
import '../../models/session_model.dart';
import '../../services/teacher_service.dart';

/// Écran de génération du QR pour une séance.
class GenerateQrScreen extends StatefulWidget {
  final int sessionId;

  const GenerateQrScreen({super.key, required this.sessionId});

  @override
  State<GenerateQrScreen> createState() => _GenerateQrScreenState();
}

class _GenerateQrScreenState extends State<GenerateQrScreen> {
  final _teacherService = TeacherService();

  int _expiryMinutes = 20;
  int _radius = 50;
  double? _latitude;
  double? _longitude;
  bool _locationLoading = false;
  String? _error;
  SessionQrPayload? _payload;

  @override
  void initState() {
    super.initState();
    _loadExistingQr();
  }

  Future<void> _loadExistingQr() async {
    try {
      final payload = await _teacherService.fetchCurrentQr(widget.sessionId);
      if (mounted && payload != null && payload.isQrValid) {
        setState(() => _payload = payload);
      }
    } catch (_) {
      // QR existant optionnel : on reste sur le formulaire de génération.
    }
  }

  Future<void> _captureLocation() async {
    setState(() => _locationLoading = true);
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        _showError('Activez la localisation GPS pour capturer la position.');
        return;
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _showError('Permission de localisation refusée.');
        return;
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );
      if (mounted) {
        setState(() {
          _latitude = double.parse(position.latitude.toStringAsFixed(7));
          _longitude = double.parse(position.longitude.toStringAsFixed(7));
        });
      }
    } catch (e) {
      _showError('Impossible de récupérer la position : $e');
    } finally {
      if (mounted) setState(() => _locationLoading = false);
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    setState(() => _error = msg);
  }

  Future<void> _generate() async {
    setState(() {
      _error = null;
    });
    try {
      final payload = await _teacherService.generateQr(
        widget.sessionId,
        expiryMinutes: _expiryMinutes,
        attendanceRadiusMeters: _radius,
        latitude: _latitude,
        longitude: _longitude,
      );
      if (!mounted) return;
      setState(() => _payload = payload);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('QR généré avec succès'),
          backgroundColor: AppTheme.successColor,
        ),
      );
    } catch (e) {
      _showError(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Générer le QR')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_error != null)
            Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.errorColor.withOpacity(.08),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline,
                      color: AppTheme.errorColor, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_error!,
                        style: const TextStyle(fontSize: 12)),
                  ),
                ],
              ),
            ),

          // ── Durée de validité ────────────────────────────────────────
          Text('Durée de validité (minutes)',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 10, label: Text('10')),
              ButtonSegment(value: 20, label: Text('20')),
              ButtonSegment(value: 30, label: Text('30')),
              ButtonSegment(value: 60, label: Text('60')),
            ],
            selected: {_expiryMinutes},
            onSelectionChanged: (v) => setState(() => _expiryMinutes = v.first),
          ),
          const SizedBox(height: 20),

          // ── Rayon de présence ────────────────────────────────────────
          Text('Rayon de présence (mètres)',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 20, label: Text('20')),
              ButtonSegment(value: 50, label: Text('50')),
              ButtonSegment(value: 100, label: Text('100')),
              ButtonSegment(value: 200, label: Text('200')),
            ],
            selected: {_radius},
            onSelectionChanged: (v) => setState(() => _radius = v.first),
          ),
          const SizedBox(height: 20),

          // ── Localisation ─────────────────────────────────────────────
          Card(
            elevation: 0,
            child: ListTile(
              leading: _locationLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(
                      _latitude != null
                          ? Icons.gps_fixed_rounded
                          : Icons.gps_off_rounded,
                      color: _latitude != null
                          ? AppTheme.successColor
                          : Colors.grey,
                    ),
              title: const Text('Localisation de la salle'),
              subtitle: Text(
                _latitude != null
                    ? '${_latitude!.toStringAsFixed(6)}, '
                        '${_longitude!.toStringAsFixed(6)}'
                    : 'Capturer la position GPS (recommandé)',
                style: const TextStyle(fontSize: 12),
              ),
              trailing: TextButton(
                onPressed: _locationLoading ? null : _captureLocation,
                child: Text(_latitude != null ? 'Reprendre' : 'Capturer'),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // ── Bouton générer ───────────────────────────────────────────
          ElevatedButton.icon(
            onPressed: _generate,
            icon: const Icon(Icons.qr_code_2_rounded),
            label: const Text('Générer le QR'),
          ),
          const SizedBox(height: 24),

          // ── QR affiché ───────────────────────────────────────────────
          if (_payload != null && _payload!.isQrValid) ...[
            Text('QR actif',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.primary.withOpacity(.2)),
              ),
              child: Column(
                children: [
                  if (_payload!.qrImageBase64 != null &&
                      _payload!.qrImageBase64!.isNotEmpty)
                    Image.memory(_decodeBase64(_payload!.qrImageBase64!),
                        width: 240, height: 240)
                  else
                    const Icon(Icons.qr_code_rounded,
                        size: 240, color: Colors.black),
                  const SizedBox(height: 12),
                  Text(
                    'Expire : ${_payload!.expiresAt?.toString() ?? '—'}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  Text(
                    'Rayon : ${_payload!.attendanceRadiusMeters} m',
                    style: TextStyle(
                        fontSize: 12, color: Colors.grey[600]),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  static Uint8List _decodeBase64(String input) {
    final comma = input.indexOf(',');
    final data = comma >= 0 ? input.substring(comma + 1) : input;
    return base64Decode(data);
  }
}
