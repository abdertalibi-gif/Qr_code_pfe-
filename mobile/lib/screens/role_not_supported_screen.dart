import 'package:flutter/material.dart';

import '../constants/app_constants.dart';
import '../constants/app_theme.dart';
import '../l10n/app_strings.dart';
import '../providers/auth_provider.dart';
import 'package:provider/provider.dart';

/// charge sur mobile (admin, department_head, program_manager, …).
class RoleNotSupportedScreen extends StatelessWidget {
  const RoleNotSupportedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 90,
                  height: 90,
                  decoration: BoxDecoration(
                    color: AppTheme.warningColor.withOpacity(.12),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.devices_other_rounded,
                    size: 44,
                    color: AppTheme.warningColor,
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Rôle non pris en charge sur mobile',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  "Ce rôle est disponible uniquement sur la version Web de l'application.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    height: 1.5,
                    color: Theme.of(context).textTheme.bodyMedium?.color,
                  ),
                ),
                const SizedBox(height: 32),
                OutlinedButton.icon(
                  onPressed: () async {
                    await context.read<AuthProvider>().logout();
                    if (context.mounted) {
                      Navigator.of(context).pushNamedAndRemoveUntil(
                        AppConstants.routeLogin,
                        (_) => false,
                      );
                    }
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text(AppStrings.signOut),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
