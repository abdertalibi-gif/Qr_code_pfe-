import 'package:flutter/material.dart';

import '../constants/app_theme.dart';

/// A full-width [ElevatedButton] that displays a [CircularProgressIndicator]
/// while [isLoading] is `true`, preventing multiple taps during async work.
class LoadingButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final bool isLoading;
  final String label;
  final IconData? icon;
  final Color? backgroundColor;
  final Color? foregroundColor;
  final double? width;
  final double height;
  final double borderRadius;
  final double fontSize;
  final FontWeight fontWeight;

  const LoadingButton({
    super.key,
    required this.onPressed,
    required this.isLoading,
    required this.label,
    this.icon,
    this.backgroundColor,
    this.foregroundColor,
    this.width,
    this.height = 52,
    this.borderRadius = 14,
    this.fontSize = 16,
    this.fontWeight = FontWeight.w600,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveBg = backgroundColor ?? AppTheme.primary;
    final effectiveFg = foregroundColor ?? Colors.white;
    final gradient = backgroundColor == null
        ? AppTheme.primaryGradient
        : LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              effectiveBg,
              Color.lerp(effectiveBg, Colors.black, 0.12)!,
            ],
          );

    return SizedBox(
      width: width ?? double.infinity,
      height: height,
      child: Opacity(
        opacity: isLoading ? 0.72 : 1,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: gradient,
            borderRadius: BorderRadius.circular(borderRadius),
            boxShadow: [
              BoxShadow(
                color: effectiveBg.withOpacity(0.28),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ElevatedButton(
            onPressed: isLoading ? null : onPressed,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.transparent,
              foregroundColor: effectiveFg,
              disabledBackgroundColor: Colors.transparent,
              disabledForegroundColor: effectiveFg.withOpacity(0.75),
              elevation: 0,
              shadowColor: Colors.transparent,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(borderRadius),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              animationDuration: const Duration(milliseconds: 200),
            ),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              transitionBuilder: (child, animation) {
                return FadeTransition(
                  opacity: animation,
                  child: ScaleTransition(
                    scale: Tween<double>(begin: 0.8, end: 1.0).animate(animation),
                    child: child,
                  ),
                );
              },
              child: isLoading
                  ? _LoadingContent(
                      key: const ValueKey('loading'),
                      color: effectiveFg,
                    )
                  : _LabelContent(
                      key: const ValueKey('label'),
                      label: label,
                      icon: icon,
                      fontSize: fontSize,
                      fontWeight: fontWeight,
                      color: effectiveFg,
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Loading content ──────────────────────────────────────────────────────────

class _LoadingContent extends StatelessWidget {
  final Color color;

  const _LoadingContent({super.key, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          'Please wait…',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w500,
            color: color,
          ),
        ),
      ],
    );
  }
}

// ─── Label content ────────────────────────────────────────────────────────────

class _LabelContent extends StatelessWidget {
  final String label;
  final IconData? icon;
  final double fontSize;
  final FontWeight fontWeight;
  final Color color;

  const _LabelContent({
    super.key,
    required this.label,
    this.icon,
    required this.fontSize,
    required this.fontWeight,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    if (icon == null) {
      return Text(
        label,
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: fontWeight,
          color: color,
          letterSpacing: 0.3,
        ),
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, size: fontSize + 4, color: color),
        const SizedBox(width: 10),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: fontWeight,
              color: color,
              letterSpacing: 0.3,
            ),
          ),
        ),
      ],
    );
  }
}
