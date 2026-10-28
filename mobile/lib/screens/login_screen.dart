import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../l10n/app_strings.dart';
import '../constants/app_constants.dart';
import '../constants/app_theme.dart';
import '../providers/auth_provider.dart';
import '../utils/validators.dart';
import '../widgets/app_logo.dart';
import '../widgets/custom_text_field.dart';
import '../widgets/loading_button.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _emailFocus = FocusNode();
  final _passwordFocus = FocusNode();

  bool _obscurePassword = true;
  bool _rememberMe = false;

  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeIn);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.08),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _animController, curve: Curves.easeOut));
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _emailFocus.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    FocusScope.of(context).unfocus();
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final authProvider = context.read<AuthProvider>();
    authProvider.clearError();

    final success = await authProvider.login(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );

    if (!mounted) return;

    if (success) {
      _routeForRole(authProvider.user?.role);
    } else {
      final msg = authProvider.errorMessage ?? AppStrings.loginFailed;
      _showErrorSnackBar(msg);
    }
  }

  /// Redirige selon le rôle après connexion.
  void _routeForRole(String? role) {
    switch (role) {
      case 'teacher':
        Navigator.of(
          context,
        ).pushReplacementNamed(AppConstants.routeTeacherHome);
      case 'student':
        Navigator.of(
          context,
        ).pushReplacementNamed(AppConstants.routeStudentHome);
      default:
        Navigator.of(
          context,
        ).pushReplacementNamed(AppConstants.routeRoleNotSupported);
    }
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.error_outline, color: Colors.white, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(message, style: const TextStyle(fontSize: 13)),
              ),
            ],
          ),
          backgroundColor: AppTheme.errorColor,
          duration: const Duration(seconds: 4),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
        systemNavigationBarColor: isDark
            ? AppTheme.darkBackground
            : AppTheme.lightBackground,
        systemNavigationBarIconBrightness: isDark
            ? Brightness.light
            : Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: isDark
            ? AppTheme.darkBackground
            : AppTheme.lightBackground,
        body: FadeTransition(
          opacity: _fadeAnim,
          child: SlideTransition(
            position: _slideAnim,
            child: SingleChildScrollView(
              physics: const ClampingScrollPhysics(),
              child: Column(
                children: [
                  // ── Hero bleu (marque) ─────────────────────────────
                  _buildHero(context),

                  // ── Carte de connexion flottante ───────────────────
                  Transform.translate(
                    offset: const Offset(0, -30),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 460),
                          child: _buildFormCard(isDark),
                        ),
                      ),
                    ),
                  ),

                  // ── Footer ─────────────────────────────────────────
                  Transform.translate(
                    offset: const Offset(0, -14),
                    child: _buildFooter(),
                  ),

                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ─── Hero ─────────────────────────────────────────────────────────────────

  Widget _buildHero(BuildContext context) {
    final topInset = MediaQuery.of(context).padding.top;

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(32)),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppTheme.primaryDark,
              AppTheme.primary,
              AppTheme.secondary,
            ],
            stops: [0, 0.55, 1],
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withValues(alpha: 0.28),
              blurRadius: 26,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Stack(
          children: [
            Positioned(top: -70, right: -45, child: _heroCircle(190)),
            Positioned(bottom: -55, left: -50, child: _heroCircle(160)),
            Padding(
              padding: EdgeInsets.fromLTRB(24, topInset + 16, 24, 58),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Marque
                  Row(
                    children: [
                      const AppLogo(
                        size: 46,
                        showShadow: false,
                        backgroundColor: Colors.white,
                        borderRadius: 14,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              AppConstants.appName,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                                letterSpacing: 0.2,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Pointage par QR code',
                              style: TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                                color: Colors.white.withValues(alpha: 0.78),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 28),

                  // Titre
                  Text(
                    AppStrings.welcomeBack,
                    style: const TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.w800,
                      height: 1.1,
                      letterSpacing: -0.5,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    AppStrings.signInSubtitle,
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.4,
                      color: Colors.white.withValues(alpha: 0.84),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Liseré orange de la marque Web
                  Container(
                    width: 46,
                    height: 4,
                    decoration: BoxDecoration(
                      gradient: AppTheme.navAccentGradient,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _heroCircle(double diameter) {
    return Container(
      width: diameter,
      height: diameter,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white.withValues(alpha: 0.06),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
          width: 1.5,
        ),
      ),
    );
  }

  // ─── Form card ────────────────────────────────────────────────────────────

  Widget _buildFormCard(bool isDark) {
    return Container(
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 24),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightSurface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.35 : 0.08),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── En-tête de carte ─────────────────────────────────────
            Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: isDark
                        ? AppTheme.primary.withValues(alpha: 0.18)
                        : AppTheme.primaryLight,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    Icons.shield_outlined,
                    size: 19,
                    color: isDark ? AppTheme.primaryOnDark : AppTheme.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        AppStrings.signInAction,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      Text(
                        'Accédez à votre espace',
                        style: Theme.of(
                          context,
                        ).textTheme.bodySmall?.copyWith(fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 20),

            // ── Email ────────────────────────────────────────────────
            CustomTextField(
              controller: _emailController,
              focusNode: _emailFocus,
              label: AppStrings.email,
              hint: AppStrings.emailHint,
              prefixIcon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.email],
              validator: Validators.validateEmail,
              onFieldSubmitted: (_) {
                FocusScope.of(context).requestFocus(_passwordFocus);
              },
            ),

            const SizedBox(height: 16),

            // ── Password ─────────────────────────────────────────────
            CustomTextField(
              controller: _passwordController,
              focusNode: _passwordFocus,
              label: AppStrings.password,
              hint: AppStrings.passwordHint,
              prefixIcon: Icons.lock_outline_rounded,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.password],
              validator: Validators.validatePassword,
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  size: 20,
                ),
                onPressed: () =>
                    setState(() => _obscurePassword = !_obscurePassword),
                splashRadius: 20,
              ),
              onFieldSubmitted: (_) => _handleLogin(),
            ),

            const SizedBox(height: 12),

            // ── Remember me + Forgot password row ─────────────────────
            Row(
              children: [
                // Remember me
                Expanded(
                  child: InkWell(
                    onTap: () => setState(() => _rememberMe = !_rememberMe),
                    borderRadius: BorderRadius.circular(8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 20,
                          height: 20,
                          child: Checkbox(
                            value: _rememberMe,
                            onChanged: (v) =>
                                setState(() => _rememberMe = v ?? false),
                            activeColor: AppTheme.primary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(4),
                            ),
                            materialTapTargetSize:
                                MaterialTapTargetSize.shrinkWrap,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            AppStrings.rememberMe,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(
                              context,
                            ).textTheme.bodyMedium?.copyWith(fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // ── Login button ─────────────────────────────────────────
            Consumer<AuthProvider>(
              builder: (context, auth, _) {
                return LoadingButton(
                  onPressed: _handleLogin,
                  isLoading: auth.isLoading,
                  label: AppStrings.signIn,
                  icon: Icons.login_rounded,
                );
              },
            ),

            const SizedBox(height: 20),

            // ── Divider ──────────────────────────────────────────────
            Row(
              children: [
                const Expanded(child: Divider()),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text(
                    AppStrings.or,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(fontSize: 13),
                  ),
                ),
                const Expanded(child: Divider()),
              ],
            ),

            const SizedBox(height: 20),

            // ── Guest / scan without login ────────────────────────────
            OutlinedButton.icon(
              onPressed: () => Navigator.of(
                context,
              ).pushReplacementNamed(AppConstants.routeHome),
              icon: const Icon(Icons.qr_code_scanner_rounded, size: 20),
              label: Text(AppStrings.continueAsGuest),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Footer ───────────────────────────────────────────────────────────────

  Widget _buildFooter() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryTint = isDark ? AppTheme.primaryOnDark : AppTheme.primary;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          // Info chip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: isDark
                  ? AppTheme.primary.withValues(alpha: 0.16)
                  : AppTheme.primaryLight,
              borderRadius: BorderRadius.circular(AppTheme.radiusSm),
              border: Border.all(
                color: isDark
                    ? AppTheme.primary.withValues(alpha: 0.35)
                    : AppTheme.primaryBorder,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.info_outline_rounded, size: 16, color: primaryTint),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    AppStrings.loginInfo,
                    style: TextStyle(
                      fontSize: 12,
                      color: primaryTint,
                      fontWeight: FontWeight.w500,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Version
          Text(
            '${AppConstants.appName} v${AppConstants.appVersion}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontSize: 12,
              color: Theme.of(
                context,
              ).colorScheme.onSurface.withValues(alpha: 0.4),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
