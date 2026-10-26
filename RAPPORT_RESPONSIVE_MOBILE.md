# Rapport d'audit et de correction mobile — PrésenceQR

Date : 26 octobre 2026  
Périmètre : interfaces web Django pour les rôles `admin`, `teacher`, `student`, `department_head`, `program_manager`  
Largeurs testées : 320, 375, 390, 430 px (+ desktop 1280/1440 px)

---

## 1. Objectif et périmètre

Audit et correction de la responsivité mobile de l'application web, sans réécriture de l'application, sans changement de règles métier, de rôles ou de base de données. Les corrections sont volontairement minimales et basées sur les styles responsives existants (`dashboard.css`, media queries), avec ajout d'un menu mobile dans `admin_base.html`.

Aucun champ, bouton, fonctionnalité ou élément de design existant n'a été supprimé.

---

## 2. Méthodologie

- Selenium avec Chrome headless et émulation mobile (`deviceMetrics` Android, DPR 3).
- Utilisation de `visualViewport.width` comme largeur réelle, car le viewport de mise en page s'élargit automatiquement en cas de débordement.
- Génération de JWT pour les utilisateurs existants (`pqr_tokens.json`) : aucun mot de passe ni donnée DB modifiée.
- Serveur de test : `http://127.0.0.1:8010`, `DJANGO_DEBUG=True`, `--noreload`.
- Vérification Django : `python manage.py check`.
- Captures DOM automatisées : débordement horizontal, hauteur de navigation, cibles tactiles, tableaux, modales, onglets.

---

## 3. Problèmes confirmés avant correction

| Problème | Preuve / impact |
|---|---|
| Barre de navigation admin trop large sur mobile | liens visibles en ligne, débordement horizontal et clipping |
| Aucun menu hamburger sur `/admin/...` | navigation inaccessible proprement sur téléphone |
| Zone utilisateur/déconnexion trop large | nom + badge + texte « Déconnexion » consomment trop de largeur |
| Entête sidebar enseignant qui se casse | boutons `+ Nouvelle séance` / `En direct` trop petits et mal alignés |
| Onglets étudiant non optimisés | risque de compression / débordement |
| Tableaux enseignant non scrollables | `.attendance-section { overflow: hidden }`, colonnes masquées |
| Modales trop larges / grilles 2 colonnes | champs hors viewport sur petits écrans |
| Navigation landing à 320 px | liens trop serrés, cible hamburger trop petite |
| Tableaux `.table-wrap` | largeur forcée à 100 %, colonnes illisibles |

---

## 4. Fichiers modifiés

1. `backend/templates/dashboard.css` — correctifs responsives partagés (nav, sidebar, onglets, tableaux, modales, cibles tactiles).
2. `backend/templates/admin_base.html` — menu hamburger mobile + JS, zone utilisateur compacte, libellé de déconnexion masquable.
3. `backend/templates/admin.html` — zone utilisateur compacte pour `/admin-ui/` (pas de liens de navigation).
4. `backend/templates/teacher.html` — libellé de déconnexion masquable.
5. `backend/templates/student.html` — libellé de déconnexion masquable.
6. `backend/templates/landing.html` — navigation mobile à 320/375/430 px.

Aucun fichier métier, modèle, vue, serializer ou règle de base de données n'a été modifié pour cette correction.

---

## 5. Correctifs appliqués

### Navigation admin (mobile)

- Ajout d'un bouton hamburger 40×40 px (`#navToggle`) dans `admin_base.html`.
- Menu déroulant vertical sous la barre, largeur complète, scroll vertical si nécessaire.
- Ouverture/fermeture par clic, clic extérieur, touche `Escape`, clic sur un lien.
- `aria-expanded` et `aria-label` mis à jour dynamiquement.
- Badge de rôle et nom utilisateur masqués progressivement selon la largeur.
- Texte « Déconnexion » masqué sous 768 px, icône conservée avec `aria-label`.

### Navigation admin (desktop/tablette)

- `nav { height: auto; min-height: var(--nav-h); }` pour éviter le clipping des liens wrappés.
- Tous les liens admin restent visibles sans débordement horizontal.

### Sidebar enseignant

- Entête wrappé proprement.
- Boutons `+ Nouvelle séance` et `En direct` : `min-height: 38px`, texte centré et wrappable.
- Largeurs adaptées à 320/375/390/430 px.

### Onglets étudiant

- Onglets en scroll horizontal masqué, sans retour à la ligne.
- Hauteur minimale 38 px.
- Entête de planning et barre de synchronisation empilés sur mobile.

### Tableaux

- `.table-wrap > table { width: max-content; min-width: 100%; }` avec scroll horizontal dans le conteneur.
- Correction supplémentaire pour les tableaux enseignant `.attendance-section` et `#tabPanelSuspicious` : scroll horizontal au lieu du clipping.
- Padding réduit sur mobile.

### Modales

- Largeur maximale 100 %, hauteur limitée au viewport.
- Grilles `1fr 1fr` forcées en une colonne sous 600 px.
- Footer wrappable, boutons pleine largeur avec `min-height: 40px`.
- Selects et champs limités à 100 % de largeur.

### Landing

- Navigation mobile compacte.
- Hamburger 40×40 px.
- Liens du menu mobile avec padding bloc.

---

## 6. Tests réels

### 6.1 Audit automatique responsive

| Largeur | Combos testés | Débordement horizontal | Erreurs |
|---|---:|---:|---:|
| 320 px | 32 pages/rôles | 0 | 0 |
| 375 px | 32 pages/rôles | 0 | 0 |
| 390 px | 32 pages/rôles | 0 | 0 |
| 430 px | 32 pages/rôles | 0 | 0 |
| **Total** | **128** | **0** | **0** |

Rôles couverts : admin, teacher, student, department_head, program_manager, public.  
Pages couvertes : `/admin-ui/`, `/admin/attendance-live/`, `/admin/attendances/`, `/admin/absences/`, `/admin/users/`, `/admin/teachers/`, `/admin/assistants/`, `/admin/students/`, `/admin/classes/`, `/admin/curriculum/`, `/admin/sessions/`, `/admin/departments/`, `/admin/filieres/`, `/admin/rooms/`, `/admin/reports/`, `/admin/statistics/`, `/admin/settings/`, `/admin/workload/`, `/teacher/`, `/student/`, `/`, `/login/`, `/attend/`, `/attend/?token=INVALID_TOKEN`.

### 6.2 Navigation mobile

- 14 liens admin dans le menu mobile.
- Hauteur minimale des liens : 40 px (`linkMin = 40`), 0 lien sous 40 px.
- Menu mobile : 320×496 px à 320 px, 375×595 px à 375 px, 390×657 px à 390/430 px.
- Dans tous les cas, le menu tient dans le viewport ou défile verticalement.
- Fermeture validée par `Escape` et par clic sur un lien.
- Hamburger : 40×40 px.
- Bouton déconnexion : 38×39 px, libellé masqué sous 768 px.
- Zone utilisateur : 38×38 px, sans débordement.

### 6.3 Sidebar enseignant

| Largeur | Boutons | Hauteur | Débordement page |
|---|---|---:|---:|
| 320 px | `+ Nouvelle séance`, `En direct` | 38 px | 0 |
| 375 px | idem | 38 px | 0 |
| 390 px | idem | 38 px | 0 |
| 430 px | idem | 38 px | 0 |

### 6.4 Onglets étudiant

- Hauteur des onglets : 45 px.
- Scroll horizontal masqué activé à 320/375 px.
- Pas de débordement horizontal à 320/375/390/430 px.

### 6.5 Tableaux

- Tableaux admin (`users`, `teachers`, `students`, `attendances`, `absences`, `sessions`, etc.) : scroll horizontal interne, pas de débordement de page.
- Tableau enseignant `attendance` : avant correction, largeur interne 575 à 695 px pour un conteneur de 286 à 396 px, donc colonnes masquées. Après correction : `overflow-x: auto`, tableau scrollable, aucun débordement de page.
- Tableau `suspicious` : 470 px dans un conteneur de 288 à 398 px, scroll horizontal activé.

### 6.6 Modales

| Modale | 320 px | 390 px | Footer visible | Body scrollable |
|---|---:|---:|---|---|
| Classe | 304×552 | 374×799 | oui | oui |
| SessionForm | 305×553 | 375×830 | oui | oui |
| Export wizard | 304×552 | 374×828 | oui | oui |
| Ajout utilisateur | 304×552 | 374×594 | oui | oui |
| Ajout enseignant | 304×552 | 374×828 | oui | oui |
| QR enseignant | 304×462 | 374×442 | oui | oui |

- Grilles `1fr 1fr` passées en une colonne sous 600 px.
- Boutons footer : `min-height: 40px`, aucune sortie du viewport.

### 6.7 Authentification et rôles

- Identifiants invalides : alerte d'erreur affichée, aucun token stocké.
- Sans token : redirection vers `/login/`.
- Token étudiant sur page admin : redirection vers `/student/`.
- Déconnexion : `access_token`, `refresh_token`, `current_user` supprimés, redirection `/login/`.
- API `/api/v1/auth/me/` : 200 avec token, 401 sans token.

### 6.8 Page publique de présence

- `/attend/?token=INVALID_TOKEN` affiche `Code QR invalide.` et tient dans le viewport à 320 et 390 px.
- Carte de présence : 272 px à 320 px, 342 px à 390 px.

### 6.9 Réinitialisation de mot de passe

- Panneau de réinitialisation : une colonne, champs de 224 px à 320 px et 294 px à 390 px.
- Page `/password-reset/.../` valide : carte 272 px à 320 px, 342 px à 390 px ; formulaire et bouton pleine largeur utile.

### 6.10 Géolocalisation et QR

- Code web inspecté : aucun usage de `getUserMedia` / `mediaDevices` dans les templates web.
- Géolocalisation testée avec override CDP : statut `✅ Position capturée (31.62950, -7.98110)`.
- En production, la géolocalisation nécessite un contexte sécurisé (HTTPS).
- La lecture QR par caméra n'est pas implémentée dans l'interface web ; elle est gérée par l'application mobile / lien profond. La modale QR et la page publique ont été testées.

### 6.11 Desktop

| Largeur | Pages | Débordement | Navigation |
|---|---|---:|---|
| 1280 px | admin classes, admin-ui, teacher, student | 0 | 14 liens visibles, toggle masqué, nav 122 px |
| 1440 px | idem | 0 | 14 liens visibles, toggle masqué, nav 122 px |

- Navigation admin desktop passe sur deux lignes si nécessaire (122 px) sans clipping.
- `/admin-ui/` conserve sa barre compacte (64 px).

### 6.12 Django

- `python manage.py check` : `System check identified no issues (0 silenced).`
- `git diff --check` : aucune erreur d'espacement.

---

## 7. Vérifications nécessaires sur téléphone physique

Ces points ne peuvent pas être validés de façon fiable par l'émulation desktop :

1. Ouverture réelle de la caméra et lecture d'un QR code (deep link vers `/attend/?token=...`).
2. Prompts natifs iOS/Android pour la géolocalisation et la caméra, et précision GPS réelle.
3. Comportement du viewport avec clavier virtuel (iOS Safari, Chrome Android).
4. Téléchargement et ouverture réelle du fichier Excel généré.
5. Fluidité du scroll horizontal des tableaux avec le doigt.
6. Lisibilité réelle des modales et formulaires sur petits écrans.
7. Comportement sur Safari iOS et Firefox Android.
8. Latence réseau réelle (3G/4G) pendant l'initialisation des pages admin.
9. Taille réelle du QR code selon la caméra et la distance.
10. Accessibilité tactile réelle des cibles de 38 à 44 px.

---

## 8. Réserves et limites

- L'émulation Chrome ne remplace pas un appareil physique pour les permissions, le clavier et la caméra.
- Certaines pages admin dépendent d'API Neon lentes ; l'initialisation peut dépasser 15 s.
- Le bouton « Export Excel » de `/admin/sessions/` n'est pas câblé dans `admin-sessions.js` (problème fonctionnel préexistant, hors périmètre responsive). La modale est responsive et l'export fonctionne via `/admin-ui/`.
- L'export `/admin-ui/` s'ouvre après chargement des données (environ 15 s selon la latence).
- La lecture QR par caméra n'est pas implémentée dans le web ; seul le flux de présence via lien est testé.

---

## 9. Conclusion

La responsivité mobile a été corrigée et vérifiée sur 128 combinaisons page/rôle aux largeurs 320, 375, 390 et 430 px, avec zéro débordement horizontal. Les navigations, tableaux, modales, formulaires, onglets et flux d'authentification sont utilisables sur mobile. Le desktop reste fonctionnel (1280/1440 px) et `python manage.py check` passe sans erreur.

Les vérifications restantes concernent uniquement le matériel physique (caméra, GPS, clavier, téléchargement réel, navigateurs mobiles).
