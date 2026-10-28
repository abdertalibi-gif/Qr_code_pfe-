# Rapport de migration — base indépendante `presenceqr_db`

Date : 28/10/2026
Projet : `attendance-system-QR`

---

## 1. Base source identifiée

| Élément | Valeur |
|---|---|
| Fournisseur | Neon (PostgreSQL managé, AWS us-east-1) |
| Version serveur | PostgreSQL 17.11 |
| Base | `neondb` |
| Schéma | `public` |
| Utilisateur | `neondb_owner` |
| Connexion | via `DATABASE_URL` dans `.env` (SSL requis) |
| Tables | 35 |
| Migrations Django | 99 |

Les identifiants et la chaîne de connexion complète ne sont pas reproduits ici.

## 2. Base cible

| Élément | Valeur |
|---|---|
| Serveur | PostgreSQL 18.4 local (service `postgresql-x64-18`, port 5432) |
| Base | `presenceqr_db` |
| Utilisateur | `postgres` (authentification locale, sans mot de passe dans le code) |
| Tables | 35 |
| Taille | 7,9 Mo |

**Point important** : `presenceqr_db` existait déjà mais **contenait 0 table** (base vide).
Aucune donnée n'a donc été écrasée.

## 3. Backup utilisé et validation

| Élément | Statut |
|---|---|
| `C:\Users\Abde\Desktop\presenceqr_backup\presenceqr.backup` | ❌ **INVALIDE — 0 octet** (fichier vide, non restaurable) |
| `C:\Users\Abde\Desktop\presenceqr_backup\presenceqr_fresh_2026-10-28.backup` | ✅ **Valide — 203 567 octets** |

Le backup imposé étant vide, aucune restauration n'était possible en l'état.
Un dump frais a donc été produit depuis la base source, en **lecture seule** :

```
pg_dump -Fc --no-owner --no-acl --verbose  →  presenceqr_fresh_2026-10-28.backup
```

Validation du fichier avec `pg_restore -l` :

- Format : CUSTOM (gzip), dump version 1.16
- 351 entrées de catalogue
- 35 `TABLE DATA`, 34 `SEQUENCE SET`, 117 `CONSTRAINT`, 81 `INDEX`

Restauration :

```
pg_restore --no-owner --no-acl -d presenceqr_db presenceqr_fresh_2026-10-28.backup
```

→ **`exit = 0`, aucune erreur**.

`--no-owner --no-acl` : le rôle `neondb_owner` n'existe pas en local. Cela ne touche **pas**
les rôles applicatifs Django (table `users.role`, `auth_permission`, groupes), qui sont des
**données** et ont été copiées intégralement.

## 4. Comptages avant / après

### Tables (identiques sur les 35)

| Table | Source | Cible |
|---|---|---|
| users | 462 | 462 |
| students | 392 | 392 |
| attendance | 525 | 525 |
| sessions | 55 | 55 |
| classes | 63 | 63 |
| modules | 647 | 647 |
| filieres | 117 | 117 |
| semestres | 10 | 10 |
| rooms | 85 | 85 |
| blocks | 11 | 11 |
| departments | 6 | 6 |
| amphitheaters | 9 | 9 |
| student_module | 433 | 433 |
| suspicious_attempts | 72 | 72 |
| password_reset_tokens | 8 | 8 |
| django_migrations | 99 | 99 |
| auth_permission | 132 | 132 |
| contact_messages | 4 | 4 |
| class_modules / class_semesters | 4 / 4 | 4 / 4 |
| users_assigned_classes | 6 | 6 |
| academic_years / faculties / semesters | 1 / 1 / 1 | 1 / 1 / 1 |
| autres tables (vides des deux côtés) | 0 | 0 |

`Compare-Object` sur les 35 tables → **aucune différence**.

### Structures et intégrité

| Contrôle | Source | Cible |
|---|---|---|
| Clés primaires | 35 | 35 |
| Clés étrangères | 55 | 55 |
| Contraintes UNIQUE | 27 | 27 |
| Index | 143 | 143 |
| Hachages mots de passe (MD5 agrégé) | `d9eeb64e…` | `d9eeb64e…` |
| Emails (MD5 agrégé) | `4d6754bc…` | `4d6754bc…` |
| Présences (MD5 id/student/session) | `2edad783…` | `2edad783…` |
| Algorithme de hash | pbkdf2_sha256 (89 car.) | pbkdf2_sha256 (89 car.) |
| Séquences | users 1128 / attendance 1444 | idem = `MAX(id)` |
| Lignes orphelines (FK) | 0 / 0 | 0 / 0 |
| Séances de l'enseignant 252 | 22 | 22 |

→ Hachages **strictement identiques** : aucun mot de passe réinitialisé, aucun compte recréé.

## 5. Erreurs / données non copiées

- Aucune erreur de restauration.
- Aucune table manquante, aucun enregistrement manquant.
- Non copiés volontairement : propriétaires et ACL PostgreSQL (`neondb_owner`), sans impact
  applicatif.
- Extension source : `plpgsql` uniquement (native, présente partout).

## 6. Fichiers de configuration modifiés

| Fichier | Modification |
|---|---|
| `.env` | `DATABASE_URL` pointe désormais sur `postgresql://postgres@127.0.0.1:5432/presenceqr_db`. L'ancienne URL Neon est conservée **en commentaire** pour rollback. |

Aucun autre fichier applicatif modifié. Aucun code source, endpoint, modèle ou interface changé.

Sauvegarde de l'ancien `.env` **hors du dépôt Git** :
`C:\Users\Abde\Desktop\presenceqr_backup\.env.source.bak`

> ⚠️ **Sécurité** : `.env` est actuellement **suivi par Git** (`git ls-files .env`), donc la
> chaîne de connexion Neon y figure déjà. Recommandation : `git rm --cached .env` +
> ajouter `.env` au `.gitignore`, puis régénérer le mot de passe Neon (il reste dans
> l'historique Git).

## 7. Commandes de lancement

```powershell
# Backend
cd "C:\Users\Abde\Desktop\attendance-system-QR (7)\attendance-system-QR\backend"
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8010

# Application mobile (tunnel USB)
$adb = "$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe"
& $adb reverse tcp:8000 tcp:8010
```

La connexion est résolue automatiquement depuis `.env` (`dj_database_url`), aucune variable
d'environnement supplémentaire n'est nécessaire.

## 8. Tests effectués

| Test | Résultat |
|---|---|
| `python manage.py check` | ✅ 0 problème |
| `python manage.py showmigrations` | ✅ 0 migration non appliquée |
| `python manage.py migrate --check` | ✅ `exit = 0` |
| Connexion Django (`select current_database()`) | ✅ `presenceqr_db` |
| `POST /api/v1/auth/login/` (mot de passe volontairement faux) | ✅ `400` « Invalid email or password » → recherche utilisateur + vérification du hash fonctionnelles |
| `GET /api/v1/auth/me/` | ✅ `200` |
| `GET /api/v1/classes/` | ✅ `200` (3 classes) |
| `GET /api/v1/sessions/` | ✅ `200` (22 séances) |
| `GET /api/v1/attendance/` | ✅ `200` (378 présences) |
| `GET /api/v1/statistics/` | ✅ `200` |
| `/login/` (web) | ✅ `200` |
| `/admin/login/` | ✅ `200` |
| `/api/v1/` sans jeton | ✅ `401` (protection active) |

> Limite connue : un login réel avec mot de passe n'a pas pu être testé, aucun mot de passe
> en clair n'étant disponible. La chaîne d'authentification est néanmoins validée (hash
> identique à la source + rejet correct d'un mauvais mot de passe).

## Conclusion

✅ Le projet fonctionne sur la base locale indépendante `presenceqr_db`.
✅ Les données existantes sont intégralement conservées et vérifiées (35/35 tables, comptages,
contraintes, index, séquences, hachages).
✅ La base source Neon n'a subi **aucune** écriture (uniquement des `SELECT` et un `pg_dump`).
✅ Aucun mot de passe réinitialisé, aucun compte recréé.
