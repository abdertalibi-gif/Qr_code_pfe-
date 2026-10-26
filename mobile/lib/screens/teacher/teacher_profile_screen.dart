import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/theme_provider.dart';

/// Profil enseignant + paramètres + déconnexion.
class TeacherProfileScreen extends StatelessWidget {
  const TeacherProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final theme = context.watch<ThemeProvider>();
    final user = auth.user;
    final isDark = theme.isDarkMode;

    return Scaffold(
      appBar: AppBar(title: const Text('Profil')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Carte identité ───────────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: AppTheme.primaryGradient,
              borderRadius: BorderRadius.circular(AppTheme.radiusLg),
            ),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 34,
                  backgroundColor: Colors.white.withOpacity(.25),
                  child: Text(
                    user?.initials ?? '?',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w700),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  user?.fullName ?? 'Enseignant',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  user?.email ?? '',
                  style: TextStyle(
                      color: Colors.white.withOpacity(.8), fontSize: 13),
                ),
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text('Enseignant',
                      style: TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Informations ─────────────────────────────────────────────
          Card(
            elevation: 0,
            child: Column(
              children: [
                _InfoTile(
                    icon: Icons.badge_outlined,
                    label: 'CIN',
                    value: (user?.cin?.isNotEmpty ?? false)
                        ? user?.cin ?? ''
                        : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.school_outlined,
                    label: 'Grade',
                    value: (user?.grade.isNotEmpty ?? false)
                        ? (user?.grade ?? '')
                        : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.science_outlined,
                    label: 'Spécialité',
                    value: (user?.speciality.isNotEmpty ?? false)
                        ? (user?.speciality ?? '')
                        : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.business_outlined,
                    label: 'Département',
                    value: (user?.departmentName?.isNotEmpty ?? false)
                        ? user?.departmentName ?? ''
                        : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.phone_outlined,
                    label: 'Téléphone',
                    value: (user?.phone.isNotEmpty ?? false)
                        ? user?.phone ?? ''
                        : '—'),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Paramètres ───────────────────────────────────────────────
          Text('Paramètres',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Card(
            elevation: 0,
            child: Column(
              children: [
                SwitchListTile(
                  secondary: Icon(
                    isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                    color: AppTheme.primary,
                  ),
                  title: const Text('Mode sombre'),
                  value: isDark,
                  onChanged: (_) => theme.toggleTheme(),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.info_outline_rounded,
                      color: AppTheme.primary),
                  title: const Text('À propos'),
                  subtitle: Text(
                      '${AppConstants.appName} v${AppConstants.appVersion}'),
                  onTap: () => showAboutDialog(
                    context: context,
                    applicationName: AppConstants.appName,
                    applicationVersion: AppConstants.appVersion,
                    applicationLegalese: 'Système de présence par QR',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Déconnexion ──────────────────────────────────────────────
          OutlinedButton.icon(
            onPressed: () async {
              final confirmed = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text(AppStrings.signOut),
                  content: const Text(AppStrings.signOutConfirm),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.of(ctx).pop(false),
                      child: const Text(AppStrings.cancel),
                    ),
                    ElevatedButton(
                      onPressed: () => Navigator.of(ctx).pop(true),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.errorColor,
                      ),
                      child: const Text(AppStrings.signOut),
                    ),
                  ],
                ),
              );
              if (confirmed == true && context.mounted) {
                await context.read<AuthProvider>().logout();
                if (context.mounted) {
                  Navigator.of(context)
                      .pushNamedAndRemoveUntil(
                          AppConstants.routeLogin, (_) => false);
                }
              }
            },
            icon: const Icon(Icons.logout_rounded, color: AppTheme.errorColor),
            label: const Text(AppStrings.signOut,
                style: TextStyle(color: AppTheme.errorColor)),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: AppTheme.errorColor.withOpacity(.5)),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppTheme.primary, size: 22),
      title: Text(label,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      trailing: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 160),
        child: Text(
          value,
          style: TextStyle(
              fontSize: 13,
              color: Theme.of(context).brightness == Brightness.dark
                  ? AppTheme.darkTextSecondary
                  : AppTheme.lightTextSecondary),
          textAlign: TextAlign.end,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}
