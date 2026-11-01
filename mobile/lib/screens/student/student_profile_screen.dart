import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/app_constants.dart';
import '../../constants/app_theme.dart';
import '../../l10n/app_strings.dart';
import '../../models/user_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/student_provider.dart';
import '../../providers/theme_provider.dart';

/// Profil étudiant : identité, informations académiques, modules, paramètres.
class StudentProfileScreen extends StatefulWidget {
  const StudentProfileScreen({super.key});

  @override
  State<StudentProfileScreen> createState() => _StudentProfileScreenState();
}

class _StudentProfileScreenState extends State<StudentProfileScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<StudentProvider>();
      if (provider.profile == null && !provider.isLoading) {
        provider.loadProfile();
      } else {
        provider.refreshProfile(silent: true);
      }
    });
  }

  Future<void> _logout(BuildContext context) async {
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
      if (!context.mounted) return;
      context.read<StudentProvider>().setTab(StudentTab.home);
      Navigator.of(context)
          .pushNamedAndRemoveUntil(AppConstants.routeLogin, (_) => false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final auth = context.watch<AuthProvider>();
    final theme = context.watch<ThemeProvider>();
    final provider = context.watch<StudentProvider>();
    final user = provider.profile ?? auth.user;
    final isDark = theme.isDarkMode;
    final profile = user?.studentProfile;
    final modules = profile?.modules ?? const <StudentModule>[];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        actions: [
          IconButton(
            tooltip: 'Actualiser',
            icon: const Icon(Icons.refresh_rounded, size: 22),
            onPressed: () => provider.refreshProfile(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          // ── Erreur de chargement du profil ──────────────────────────
          if (provider.errorMessage != null)
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.errorColor.withOpacity(.08),
                borderRadius: BorderRadius.circular(AppTheme.radius),
                border: Border.all(color: AppTheme.errorColor.withOpacity(.18)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline,
                      color: AppTheme.errorColor, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      provider.errorMessage!,
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),

          // ── Carte identité ───────────────────────────────────────────
          _IdentityCard(user: user, profile: profile),
          const SizedBox(height: 22),

          // ── Informations personnelles / académiques ──────────────────
          _SectionTitle(
            icon: Icons.person_outline_rounded,
            title: 'Informations personnelles',
          ),
          const SizedBox(height: 10),
          Card(
            elevation: 0,
            child: Column(
              children: [
                _InfoTile(
                    icon: Icons.fingerprint_rounded,
                    label: 'ID étudiant',
                    value: profile != null ? '#${profile.id}' : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.qr_code_rounded,
                    label: 'Code Massar',
                    value: profile?.codeMassar ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.confirmation_number_outlined,
                    label: 'Code Apogée',
                    value: (profile?.codeApogee?.isNotEmpty ?? false)
                        ? profile!.codeApogee!
                        : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.school_outlined,
                    label: 'Classe',
                    value: profile?.classeName ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.account_tree_outlined,
                    label: 'Filière',
                    value: profile?.filiereName ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.event_note_outlined,
                    label: 'Semestre',
                    value: profile?.semestreName ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.stairs_outlined,
                    label: 'Niveau',
                    value: profile?.niveau ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.date_range_outlined,
                    label: 'Année universitaire',
                    value: profile?.academicYear ?? '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.badge_outlined,
                    label: 'CIN',
                    value: user?.cin?.isNotEmpty == true ? user!.cin! : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.phone_outlined,
                    label: 'Téléphone',
                    value: user?.phone.isNotEmpty == true ? user!.phone : '—'),
                const Divider(height: 1),
                _InfoTile(
                    icon: Icons.calendar_today_outlined,
                    label: 'Inscrit depuis',
                    value: _formatDate(profile?.createdAt ?? user?.createdAt)),
              ],
            ),
          ),
          const SizedBox(height: 22),

          // ── Modules de l'étudiant ────────────────────────────────────
          Row(
            children: [
              Expanded(
                child: _SectionTitle(
                  icon: Icons.menu_book_outlined,
                  title: 'Mes modules',
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isDark
                      ? AppTheme.primary.withOpacity(.18)
                      : AppTheme.primarySoft,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '${modules.length}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (modules.length > 1)
            Text(
              'Toutes vos inscriptions',
              style: TextStyle(
                fontSize: 12,
                color: isDark
                    ? AppTheme.darkTextSecondary
                    : AppTheme.lightTextSecondary,
              ),
            )
          else if ((profile?.semestreName ?? '').isNotEmpty)
            Text(
              'Semestre ${profile!.semestreName}'
              '${(profile.filiereName ?? '').isNotEmpty ? ' · ${profile.filiereName}' : ''}',
              style: TextStyle(
                fontSize: 12,
                color: isDark
                    ? AppTheme.darkTextSecondary
                    : AppTheme.lightTextSecondary,
              ),
            ),
          const SizedBox(height: 10),
          if (modules.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                borderRadius: BorderRadius.circular(AppTheme.radius),
                border: Border.all(
                  color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.menu_book_outlined,
                      size: 22,
                      color: isDark ? AppTheme.darkMuted : AppTheme.lightMuted),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      "Aucun module n'est rattaché à votre inscription.",
                      style: TextStyle(
                        fontSize: 13,
                        color: isDark
                            ? AppTheme.darkTextSecondary
                            : AppTheme.lightTextSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            )
          else
            ...modules.map((module) => _ModuleCard(module: module)),
          const SizedBox(height: 22),

          // ── Paramètres ───────────────────────────────────────────────
          const _SectionTitle(
            icon: Icons.settings_outlined,
            title: 'Paramètres',
          ),
          const SizedBox(height: 10),
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
          const SizedBox(height: 22),

          // ── Déconnexion ──────────────────────────────────────────────
          OutlinedButton.icon(
            onPressed: () => _logout(context),
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

  static String _formatDate(String? value) {
    if (value == null || value.isEmpty) return '—';
    return value.length >= 10 ? value.substring(0, 10) : value;
  }
}

// ─── Carte identité ──────────────────────────────────────────────────────────

class _IdentityCard extends StatelessWidget {
  final UserModel? user;
  final StudentProfile? profile;

  const _IdentityCard({required this.user, required this.profile});

  @override
  Widget build(BuildContext context) {
    final details = [profile?.filiereName, profile?.semestreName]
        .where((value) => value != null && value.isNotEmpty)
        .cast<String>()
        .join(' · ');

    return Container(
      decoration: BoxDecoration(
        gradient: AppTheme.primaryGradient,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primary.withOpacity(.28),
            blurRadius: 22,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Stack(
        children: [
          // Cercles décoratifs discrets.
          Positioned(
            right: -28,
            top: -34,
            child: Container(
              width: 130,
              height: 130,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withOpacity(.08),
              ),
            ),
          ),
          Positioned(
            right: 42,
            bottom: -54,
            child: Container(
              width: 110,
              height: 110,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.accent.withOpacity(.16),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 34,
                  backgroundColor: Colors.white.withOpacity(.22),
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
                  user?.fullName ?? AppStrings.student,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 19,
                      fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  user?.email ?? '',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: Colors.white.withOpacity(.8), fontSize: 13),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.center,
                  children: [
                    _HeroPill(
                      icon: Icons.school_outlined,
                      label: profile?.classeName ?? 'Étudiant',
                    ),
                    _HeroPill(
                      icon: Icons.fingerprint_rounded,
                      label: profile != null ? 'ID #${profile!.id}' : 'ID —',
                    ),
                  ],
                ),
                if (details.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    details,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(.72),
                      fontSize: 12,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroPill extends StatelessWidget {
  final IconData icon;
  final String label;

  const _HeroPill({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.16),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: Colors.white),
          const SizedBox(width: 5),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 210),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Titre de section ───────────────────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;

  const _SectionTitle({required this.icon, required this.title});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      children: [
        Icon(icon,
            size: 18,
            color: isDark ? AppTheme.primaryOnDark : AppTheme.primary),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}

// ─── Ligne d'information ────────────────────────────────────────────────────

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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      leading: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          color: isDark
              ? AppTheme.primary.withOpacity(.16)
              : AppTheme.primarySoft,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: AppTheme.primary, size: 18),
      ),
      title: Text(label,
          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
      trailing: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 170),
        child: Text(
          value,
          style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: isDark
                  ? AppTheme.darkTextSecondary
                  : AppTheme.lightTextSecondary),
          textAlign: TextAlign.end,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}

// ─── Carte module ───────────────────────────────────────────────────────────

class _ModuleCard extends StatelessWidget {
  final StudentModule module;

  const _ModuleCard({required this.module});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final initial =
        module.name.isNotEmpty ? module.name[0].toUpperCase() : '?';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: isDark
                  ? AppTheme.primary.withOpacity(.18)
                  : AppTheme.primarySoft,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isDark
                    ? AppTheme.primary.withOpacity(.35)
                    : AppTheme.primaryBorder,
              ),
            ),
            child: Center(
              child: Text(
                initial,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  module.name,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 5),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    if (module.code.isNotEmpty)
                      _ModuleChip(
                        label: module.code,
                        highlighted: true,
                      ),
                    if (module.semestreName.isNotEmpty)
                      _ModuleChip(label: module.semestreName),
                    if (module.filiereName.isNotEmpty)
                      _ModuleChip(label: module.filiereName),
                    if (module.coefficient > 0)
                      _ModuleChip(label: 'Coef. ${module.coefficient}'),
                    if (module.teacherName.isNotEmpty)
                      _ModuleChip(label: module.teacherName),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModuleChip extends StatelessWidget {
  final String label;
  final bool highlighted;

  const _ModuleChip({required this.label, this.highlighted = false});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: highlighted
            ? (isDark
                ? AppTheme.primary.withOpacity(.2)
                : AppTheme.primarySoft)
            : (isDark ? AppTheme.darkDivider : AppTheme.lightDivider),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w600,
          color: highlighted
              ? (isDark ? AppTheme.primaryOnDark : AppTheme.primary)
              : (isDark
                  ? AppTheme.darkTextSecondary
                  : AppTheme.lightTextSecondary),
        ),
      ),
    );
  }
}
