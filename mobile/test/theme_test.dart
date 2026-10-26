// Vérifie que le thème mobile utilise bien les jetons du design system Web
// défini dans backend/templates/dashboard.css (aucune couleur inventée).
//
// Ces tests restent volontairement statiques : construire `ThemeData` déclenche
// le chargement réseau de Google Fonts, indisponible dans l'environnement de
// test. Le rendu réel des thèmes clair/sombre est couvert par
// `overflow_screen_test.dart`.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:attendance_app/constants/app_theme.dart';

void main() {
  group('Jetons de couleur alignés sur dashboard.css', () {
    test('Palette principale', () {
      expect(AppTheme.primary, const Color(0xFF0F7DB8));
      expect(AppTheme.primaryHover, const Color(0xFF0D6EA3));
      expect(AppTheme.primaryDark, const Color(0xFF0B5E8E));
      expect(AppTheme.primarySoft, const Color(0xFFE6F2F9));
      expect(AppTheme.primaryLight, const Color(0xFFF0F7FC));
      expect(AppTheme.secondary, const Color(0xFF2196D3));
      expect(AppTheme.accent, const Color(0xFFF28C28));
    });

    test('Surfaces et texte', () {
      expect(AppTheme.lightBackground, const Color(0xFFF8FAFC));
      expect(AppTheme.lightSurface, const Color(0xFFFFFFFF));
      expect(AppTheme.lightCard, const Color(0xFFFFFFFF));
      expect(AppTheme.lightTextPrimary, const Color(0xFF12324A));
      expect(AppTheme.lightTextSecondary, const Color(0xFF6B7280));
      expect(AppTheme.lightMuted, const Color(0xFF9CA3AF));
      expect(AppTheme.lightBorder, const Color(0xFFE5E7EB));
      expect(AppTheme.lightDivider, const Color(0xFFF3F4F6));
    });

    test('Couleurs sémantiques', () {
      expect(AppTheme.successColor, const Color(0xFF10B981));
      expect(AppTheme.successSoft, const Color(0xFFECFDF5));
      expect(AppTheme.errorColor, const Color(0xFFEF4444));
      expect(AppTheme.warningColor, const Color(0xFFF59E0B));
      expect(AppTheme.warningInk, const Color(0xFF92400E));
      expect(AppTheme.purple, const Color(0xFF8B5CF6));
    });

    test('Le thème sombre réutilise les teintes de marque', () {
      expect(AppTheme.darkBackground, const Color(0xFF0B1220));
      expect(AppTheme.darkSurface, const Color(0xFF111C2E));
      expect(AppTheme.darkCard, const Color(0xFF16233A));
      expect(AppTheme.darkTextPrimary, const Color(0xFFE6F2F9));
      expect(AppTheme.primaryOnDark, const Color(0xFF42A5F5));
    });
  });

  group('Dégradés et rayons Web', () {
    test('Bouton principal (#0F7DB8 → #2196D3)', () {
      expect(AppTheme.primaryGradient.colors,
          [AppTheme.primary, AppTheme.secondary]);
    });

    test('Succès (#10B981 → #059669)', () {
      expect(AppTheme.successGradient.colors,
          [AppTheme.successColor, const Color(0xFF059669)]);
    });

    test('Ligne orange du navbar Web', () {
      expect(AppTheme.navAccentGradient.colors, [
        AppTheme.accent,
        const Color(0xFFFFA94D),
        AppTheme.accent,
      ]);
    });

    test('Rayons Web : carte 14, modale 24, champs 10', () {
      expect(AppTheme.radiusSm, 10);
      expect(AppTheme.radius, 14);
      expect(AppTheme.radiusLg, 18);
      expect(AppTheme.radiusXl, 24);
    });
  });
}
