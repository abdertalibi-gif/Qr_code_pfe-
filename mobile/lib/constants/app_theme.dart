import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design tokens for the PrÃ©senceQR mobile app.
///
/// Every value below mirrors the shared Web/Desktop design system defined in
/// `backend/templates/dashboard.css`:
///   --primary: #0F7DB8  --secondary: #2196D3  --accent: #F28C28
///   --bg-section: #F8FAFC  --text: #12324A  --border: #E5E7EB
///   --font: 'Inter'
///
/// Keeping the Web tokens here (instead of inventing a mobile palette) means a
/// colour change on the portal only has to be reflected in this one file.
class AppTheme {
  // â”€â”€â”€ Brand Palette (Web tokens) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static const Color primary = Color(0xFF0F7DB8);
  static const Color primaryHover = Color(0xFF0D6EA3);
  static const Color primaryDark = Color(0xFF0B5E8E);
  static const Color primarySoft = Color(0xFFE6F2F9);
  static const Color primaryLight = Color(0xFFF0F7FC);
  static const Color primaryBorder = Color(0x330F7DB8);
  static const Color secondary = Color(0xFF2196D3);

  static const Color accent = Color(0xFFF28C28);
  static const Color accentHover = Color(0xFFE07D1A);
  static const Color accentSoft = Color(0xFFFFF3E6);

  static const Color successColor = Color(0xFF10B981);
  static const Color successSoft = Color(0xFFECFDF5);
  static const Color errorColor = Color(0xFFEF4444);
  static const Color errorSoft = Color(0xFFFEF2F2);
  static const Color warningColor = Color(0xFFF59E0B);
  static const Color warningSoft = Color(0xFFFFFBEB);
  static const Color warningInk = Color(0xFF92400E);
  static const Color warningBorder = Color(0x33F59E0B);
  static const Color purple = Color(0xFF8B5CF6);
  static const Color purpleSoft = Color(0xFFF5F3FF);
  static const Color teal = Color(0xFF14B8A6);
  static const Color tealSoft = Color(0xFFCCFBF1);
  static const Color infoColor = Color(0xFF2196D3);

  // Light surfaces
  static const Color lightBackground = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightTextPrimary = Color(0xFF12324A);
  static const Color lightTextSecondary = Color(0xFF6B7280);
  static const Color lightMuted = Color(0xFF9CA3AF);
  static const Color lightBorder = Color(0xFFE5E7EB);
  static const Color lightBorderStrong = Color(0xFFD1D5DB);
  static const Color lightDivider = Color(0xFFF3F4F6);

  // Dark surfaces. The Web portal is light-only; dark values reuse the same
  // brand hues on the portal's deep-blue text colour (#12324A).
  static const Color darkBackground = Color(0xFF0B1220);
  static const Color darkSurface = Color(0xFF111C2E);
  static const Color darkCard = Color(0xFF16233A);
  static const Color darkTextPrimary = Color(0xFFE6F2F9);
  static const Color darkTextSecondary = Color(0xFF9CA3AF);
  static const Color darkMuted = Color(0xFF6B7280);
  static const Color darkBorder = Color(0xFF24344D);
  static const Color darkDivider = Color(0xFF1E2D42);
  static const Color primaryOnDark = Color(0xFF42A5F5);

  // â”€â”€â”€ Gradients (copied from dashboard.css) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, secondary],
  );

  static const LinearGradient primaryGradientHover = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primaryHover, Color(0xFF1E88E5)],
  );

  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [successColor, Color(0xFF059669)],
  );

  static const LinearGradient dangerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [errorColor, Color(0xFFDC2626)],
  );

  /// Full-bleed hero gradient used by the Web login/landing hero.
  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0A4F73),
      Color(0xFF0C6A9A),
      Color(0xFF0F7DB8),
      Color(0xFF1E90D0),
      Color(0xFF42A5F5),
    ],
    stops: [0.0, 0.25, 0.5, 0.75, 1.0],
  );

  static const LinearGradient heroGradientDark = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF071A2A), Color(0xFF0A4F73), Color(0xFF0F7DB8)],
    stops: [0.0, 0.55, 1.0],
  );

  /// Thin orange accent line under the Web navbar.
  static const LinearGradient navAccentGradient = LinearGradient(
    colors: [accent, Color(0xFFFFA94D), accent],
  );

  // â”€â”€â”€ Radii (Web: 10 / 14 / 18 / 24 px) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static const double radiusSm = 10;
  static const double radius = 14;
  static const double radiusLg = 18;
  static const double radiusXl = 24;

  // â”€â”€â”€ Themes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static ThemeData get lightTheme => _buildTheme(Brightness.light);
  static ThemeData get darkTheme => _buildTheme(Brightness.dark);

  static ThemeData _buildTheme(Brightness brightness) {
    final isLight = brightness == Brightness.light;
    final background = isLight ? lightBackground : darkBackground;
    final surface = isLight ? lightSurface : darkSurface;
    final card = isLight ? lightCard : darkCard;
    final textPrimary = isLight ? lightTextPrimary : darkTextPrimary;
    final textSecondary = isLight ? lightTextSecondary : darkTextSecondary;
    final muted = isLight ? lightMuted : darkMuted;
    final border = isLight ? lightBorder : darkBorder;
    final divider = isLight ? lightDivider : darkDivider;
    final primaryColor = isLight ? primary : primaryOnDark;
    final softPrimary = isLight ? primarySoft : primary.withOpacity(0.18);
    final textTheme = _textTheme(brightness);

    final base =
        isLight ? ThemeData.light(useMaterial3: true) : ThemeData.dark(useMaterial3: true);

    return base.copyWith(
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        brightness: brightness,
      ).copyWith(
        primary: primaryColor,
        onPrimary: Colors.white,
        secondary: accent,
        onSecondary: Colors.white,
        error: errorColor,
        onError: Colors.white,
        surface: surface,
        onSurface: textPrimary,
        surfaceContainerHighest: card,
        outline: border,
        outlineVariant: divider,
        surfaceTint: Colors.transparent,
      ),
      scaffoldBackgroundColor: background,
      canvasColor: background,
      textTheme: textTheme,
      primaryTextTheme: textTheme,
      iconTheme: IconThemeData(color: textSecondary, size: 22),
      primaryIconTheme: IconThemeData(color: textPrimary, size: 22),
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleSpacing: 16,
        shadowColor: Colors.black12,
        shape: Border(
          bottom: BorderSide(color: accent.withOpacity(0.8), width: 3),
        ),
        titleTextStyle: _style(
          18,
          FontWeight.w700,
          textPrimary,
          letterSpacing: -0.2,
        ),
        iconTheme: IconThemeData(color: textPrimary, size: 22),
        actionsIconTheme: IconThemeData(color: textPrimary, size: 22),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: card,
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.black.withOpacity(0.06),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radius),
          side: BorderSide(color: border),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          disabledBackgroundColor: primaryColor.withOpacity(0.45),
          disabledForegroundColor: Colors.white70,
          elevation: 0,
          shadowColor: Colors.transparent,
          minimumSize: const Size(double.infinity, 50),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
          textStyle: _style(15, FontWeight.w600, Colors.white),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryColor,
          minimumSize: const Size(double.infinity, 50),
          side: BorderSide(color: primaryColor.withOpacity(0.35), width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusSm),
          ),
          textStyle: _style(15, FontWeight.w600, primaryColor),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryColor,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: _style(14, FontWeight.w600, primaryColor),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: BorderSide(color: border, width: 1.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: BorderSide(color: border, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: BorderSide(color: primaryColor, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: errorColor),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: errorColor, width: 2),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: BorderSide(color: border.withOpacity(0.6)),
        ),
        hintStyle: _style(14, FontWeight.w400, muted),
        labelStyle: _style(14, FontWeight.w500, textSecondary),
        floatingLabelStyle: _style(13, FontWeight.w600, primaryColor),
        errorStyle: _style(12, FontWeight.w500, errorColor),
        helperStyle: _style(12, FontWeight.w400, textSecondary),
        prefixIconColor: textSecondary,
        suffixIconColor: textSecondary,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: isLight ? primarySoft : primary.withOpacity(0.16),
        selectedColor: primaryColor,
        secondarySelectedColor: primaryColor,
        side: isLight
            ? const BorderSide(color: primaryBorder)
            : BorderSide(color: primary.withOpacity(0.35)),
        labelStyle: _style(12, FontWeight.w600, primaryColor),
        secondaryLabelStyle: _style(12, FontWeight.w700, Colors.white),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(100),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: divider,
        thickness: 1,
        space: 1,
      ),
      listTileTheme: ListTileThemeData(
        iconColor: primaryColor,
        textColor: textPrimary,
        subtitleTextStyle: _style(12, FontWeight.w400, textSecondary),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 24,
        shadowColor: Colors.black.withOpacity(0.18),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusXl),
        ),
        titleTextStyle: _style(18, FontWeight.w700, textPrimary),
        contentTextStyle: _style(14, FontWeight.w400, textSecondary, height: 1.5),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        modalBackgroundColor: surface,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(radiusXl)),
        ),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: primaryColor,
        unselectedLabelColor: textSecondary,
        indicatorColor: primaryColor,
        indicatorSize: TabBarIndicatorSize.tab,
        dividerColor: border,
        labelStyle: _style(13, FontWeight.w700, primaryColor),
        unselectedLabelStyle: _style(13, FontWeight.w500, textSecondary),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 68,
        indicatorColor: softPrimary,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? primaryColor : muted,
            size: selected ? 24 : 22,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return _style(
            11,
            selected ? FontWeight.w700 : FontWeight.w500,
            selected ? primaryColor : textSecondary,
          );
        }),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: primaryColor,
        unselectedItemColor: muted,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: _style(11, FontWeight.w700, primaryColor),
        unselectedLabelStyle: _style(11, FontWeight.w500, textSecondary),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        elevation: 2,
        focusElevation: 2,
        hoverElevation: 3,
        highlightElevation: 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSm),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: isLight ? lightTextPrimary : darkCard,
        contentTextStyle: _style(
          13,
          FontWeight.w500,
          isLight ? Colors.white : darkTextPrimary,
        ),
        actionTextColor: isLight ? const Color(0xFF7DD3FC) : accent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSm),
        ),
        insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(color: primaryColor),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return primaryColor;
          return isLight ? Colors.white : darkTextSecondary;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return primaryColor.withOpacity(0.45);
          }
          return isLight ? lightDivider : darkBorder;
        }),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return primaryColor;
          return Colors.transparent;
        }),
        checkColor: const WidgetStatePropertyAll(Colors.white),
        side: BorderSide(color: border, width: 1.5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(4),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          side: BorderSide(color: border),
        ),
        textStyle: _style(14, FontWeight.w500, textPrimary),
      ),
      datePickerTheme: DatePickerThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        headerBackgroundColor: primaryColor,
        headerForegroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusLg),
        ),
      ),
      timePickerTheme: TimePickerThemeData(
        backgroundColor: surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusLg),
        ),
      ),
    );
  }

  // â”€â”€â”€ Typography (Inter, like the Web portal) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  static TextTheme _textTheme(Brightness brightness) {
    final isLight = brightness == Brightness.light;
    final textPrimary = isLight ? lightTextPrimary : darkTextPrimary;
    final textSecondary = isLight ? lightTextSecondary : darkTextSecondary;
    final base =
        isLight ? ThemeData.light(useMaterial3: true).textTheme : ThemeData.dark(useMaterial3: true).textTheme;

    return GoogleFonts.interTextTheme(base).copyWith(
      displayLarge: _style(32, FontWeight.w800, textPrimary, letterSpacing: -0.8),
      displayMedium: _style(28, FontWeight.w800, textPrimary, letterSpacing: -0.6),
      headlineLarge: _style(26, FontWeight.w800, textPrimary, letterSpacing: -0.5),
      headlineMedium: _style(22, FontWeight.w700, textPrimary, letterSpacing: -0.3),
      titleLarge: _style(18, FontWeight.w700, textPrimary, letterSpacing: -0.2),
      titleMedium: _style(16, FontWeight.w600, textPrimary),
      bodyLarge: _style(16, FontWeight.w400, textPrimary, height: 1.55),
      bodyMedium: _style(14, FontWeight.w400, textSecondary, height: 1.5),
      bodySmall: _style(12, FontWeight.w400, textSecondary, height: 1.4),
      labelLarge: _style(14, FontWeight.w600, textPrimary),
      labelMedium: _style(12, FontWeight.w600, textSecondary),
      labelSmall: _style(11, FontWeight.w600, textSecondary),
    );
  }

  static TextStyle _style(
    double size,
    FontWeight weight,
    Color color, {
    double? letterSpacing,
    double? height,
  }) {
    return GoogleFonts.inter(
      fontSize: size,
      fontWeight: weight,
      color: color,
      letterSpacing: letterSpacing,
      height: height,
    );
  }
}
