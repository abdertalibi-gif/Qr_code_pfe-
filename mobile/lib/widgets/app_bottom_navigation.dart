import 'package:flutter/material.dart';

import '../constants/app_theme.dart';

/// Bottom navigation matching the Web portal navbar:
/// white surface, brand-blue active item, soft blue pill and the thin orange
/// accent line used under `nav` in `dashboard.css`.
class AppBottomNavigation extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final List<NavigationDestination> destinations;

  /// Optional label size override (the teacher bar has 5 destinations and
  /// needs a slightly smaller label on 320 px screens).
  final double? labelFontSize;

  const AppBottomNavigation({
    super.key,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.destinations,
    this.labelFontSize,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final surface = isDark ? AppTheme.darkSurface : AppTheme.lightSurface;
    final border = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final secondary =
        isDark ? AppTheme.darkTextSecondary : AppTheme.lightTextSecondary;
    final selectedColor = isDark ? AppTheme.primaryOnDark : AppTheme.primary;

    final base = theme.navigationBarTheme;
    final resolvedTheme = labelFontSize == null
        ? base
        : base.copyWith(
            labelTextStyle: WidgetStateProperty.resolveWith((states) {
              final selected = states.contains(WidgetState.selected);
              return TextStyle(
                fontSize: labelFontSize,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: selected ? selectedColor : secondary,
                fontFamily: 'Inter',
              );
            }),
          );

    return DecoratedBox(
      decoration: BoxDecoration(
        color: surface,
        border: Border(top: BorderSide(color: border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Thin orange accent line, same as the Web navbar.
          Container(
            height: 3,
            decoration: const BoxDecoration(
              gradient: AppTheme.navAccentGradient,
            ),
          ),
          NavigationBarTheme(
            data: resolvedTheme,
            child: NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: onDestinationSelected,
              destinations: destinations,
              elevation: 0,
              backgroundColor: surface,
              surfaceTintColor: Colors.transparent,
              indicatorColor: isDark
                  ? AppTheme.primary.withOpacity(0.20)
                  : AppTheme.primarySoft,
            ),
          ),
        ],
      ),
    );
  }
}
