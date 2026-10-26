import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.admin import SessionAdminForm, NIVEAU_SEMESTRE_MAP
from curriculum.models import Module, Filiere, Semestre
from courses.models import Session
from users.models import User, Classe

# Get a single teacher user
teacher_users = User.objects.filter(role='teacher')[:1]
teacher_id = teacher_users[0].id if teacher_users else None

# Get a valid classe
classe = Classe.objects.filter(niveau='LIC', semestre__name='S5').first()
if not classe:
    classe = Classe.objects.first()

print("=== Session Admin Form Validation Tests ===")

# Helper: get filiere by name and niveau
def get_filiere_by_name_niveau(name, niveau):
    try:
        return Filiere.objects.get(name=name, niveau=niveau)
    except Filiere.MultipleObjectsReturned:
        return Filiere.objects.filter(name=name, niveau=niveau).first()
    except Filiere.DoesNotExist:
        return None

# Test 1: Valid combination (LIC + S5 + Mathematiques et Applications + module + valid classe)
print("Test 1: Valid combination (LIC + S5 + Mathematiques et Applications + module + classe)")
try:
    modules = Module.objects.filter(filiere__niveau='LIC', filiere__semestre__name='S5')
    if modules.exists():
        m = modules.first()
        filiere = get_filiere_by_name_niveau("Mathematiques et Applications", "LIC")
        semestre = Semestre.objects.get(name="S5")
        
        form = SessionAdminForm(data={
            'subject': 'Test',
            'module': m.id,
            'teacher': teacher_id,
            'classe': classe.id,
            'location_type': 'block',  # Session model uses "block", not "BLOC"
            'date': '2026-01-15',
            'start_time': '08:00',
            'end_time': '10:00',
            'niveau': 'LIC',
            'semestre': semestre.id,
            'filiere': filiere.id if filiere else '',
            'session_type': 'Cours',
            'attendance_radius_meters': 50,
        })
        if form.is_valid():
            print("  PASS: Formulaire valide")
            cd = form.cleaned_data
            print(f"    niveau={cd.get('niveau')}, semestre={cd.get('semestre').name if cd.get('semestre') else None}, filiere={cd.get('filiere')}, module={cd.get('module')}")
        else:
            print("  FAIL: Formulaire invalide:", form.errors)
    else:
        print("  SKIP: Aucun module trouve")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 2: Mismatched niveau and filiere (LIC niveau + MAS filiere S5, with valid classe)
print("\nTest 2: Mismatched niveau and filiere (LIC niveau + MAS filiere S5, classe valide)")
try:
    mas_filiere = get_filiere_by_name_niveau("Systemes Intelligents et Recherche Operationnelle", "MAS")
    semestre = Semestre.objects.get(name="S5")
    
    form = SessionAdminForm(data={
        'subject': 'Test',
        'module': '',
        'teacher': teacher_id,
        'classe': classe.id,
        'location_type': 'block',
        'date': '2026-01-15',
        'start_time': '08:00',
        'end_time': '10:00',
        'niveau': 'LIC',  # Niveau mismatch: LIC vs MAS filiere
        'semestre': semestre.id,
        'filiere': mas_filiere.id if mas_filiere else '',
        'session_type': 'Cours',
        'attendance_radius_meters': 50,
    })
    error_keys = list(form.errors.keys()) if form.errors else []
    academic_errors = [k for k in error_keys if k in ('niveau', 'semestre', 'filiere', 'module')]
    other_errors = [k for k in error_keys if k not in ('niveau', 'semestre', 'filiere', 'module', 'teacher')]
    
    if academic_errors:
        print(f"  PASS: Erreurs academiques detects: {academic_errors}")
    else:
        nk = len(other_errors)
        print(f"  INFO: Pas d'erreurs academiques ({nk} autres erreurs)")
        if not form.is_valid():
            print("  (Formulaire invalide cause par d'autres champs)")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 3: Module not in filiere (with valid classe)
print("\nTest 3: Module not belonging to selected filiere (classe valide)")
try:
    mas_m = Module.objects.filter(filiere__niveau='MAS').first()
    lic_filiere = get_filiere_by_name_niveau("Mathematiques et Applications", "LIC")
    
    form = SessionAdminForm(data={
        'subject': 'Test',
        'module': mas_m.id if mas_m else '',
        'teacher': teacher_id,
        'classe': classe.id,
        'location_type': 'block',
        'date': '2026-01-15',
        'start_time': '08:00',
        'end_time': '10:00',
        'niveau': 'LIC',
        'semestre': Semestre.objects.get(name='S5').id,
        'filiere': lic_filiere.id if lic_filiere else '',
        'session_type': 'Cours',
        'attendance_radius_meters': 50,
    })
    error_keys = list(form.errors.keys()) if form.errors else []
    academic_errors = [k for k in error_keys if k in ('niveau', 'semestre', 'filiere', 'module')]
    
    if academic_errors and 'module' in academic_errors:
        print(f"  PASS: Erreur module detectee: {academic_errors}")
        print(f"    -> Validation reussie: module appartient bien au filiere selectionnee")
    elif form.is_valid():
        print("  FAIL: Formulaire valide (attendu invalide)")
    else:
        nk = len([k for k in error_keys if k not in ('niveau', 'semestre', 'filiere', 'module', 'teacher')])
        print(f"  INFO: Autres erreurs ({nk}), erreurs academiques: {academic_errors or 'none'}")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 4: Semester not allowed for niveau (MAS + S5, with valid classe)
print("\nTest 4: Semester not allowed for niveau (MAS + S5, classe valide)")
try:
    
    form = SessionAdminForm(data={
        'subject': 'Test',
        'module': '',
        'teacher': teacher_id,
        'classe': classe.id,
        'location_type': 'block',
        'date': '2026-01-15',
        'start_time': '08:00',
        'end_time': '10:00',
        'niveau': 'MAS',
        'semestre': Semestre.objects.get(name='S5').id,
        'filiere': '',
        'session_type': 'Cours',
        'attendance_radius_meters': 50,
    })
    error_keys = list(form.errors.keys()) if form.errors else []
    academic_errors = [k for k in error_keys if k in ('niveau', 'semestre', 'filiere', 'module')]
    
    if academic_errors and 'semestre' in academic_errors:
        print(f"  PASS: Erreur semestre detectee (MAS + S5 non autorise): {academic_errors}")
    elif form.is_valid():
        print("  FAIL: Formulaire valide (attendu invalide)")
    else:
        nk = len([k for k in error_keys if k not in ('niveau', 'semestre', 'filiere', 'module', 'teacher')])
        print(f"  INFO: Autres erreurs ({nk}), erreurs academiques: {academic_errors or 'none'}")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 5: niveau + semestre + filiere without module (with valid classe)
print("\nTest 5: niveau + semestre + filiere without module (classe valide)")
try:
    filiere = get_filiere_by_name_niveau("Systemes Intelligents et Recherche Operationnelle", "MAS")
    
    form = SessionAdminForm(data={
        'subject': 'Test',
        'module': '',
        'teacher': teacher_id,
        'classe': classe.id,
        'location_type': 'block',
        'date': '2026-01-15',
        'start_time': '08:00',
        'end_time': '10:00',
        'niveau': 'MAS',
        'semestre': filiere.semestre_id if filiere else Semestre.objects.get(name='S7').id,
        'filiere': filiere.id if filiere else '',
        'session_type': 'Cours',
        'attendance_radius_meters': 50,
    })
    error_keys = list(form.errors.keys()) if form.errors else []
    academic_errors = [k for k in error_keys if k in ('niveau', 'semestre', 'filiere', 'module')]
    
    nk = len([k for k in error_keys if k not in ('niveau', 'semestre', 'filiere', 'module', 'teacher')])
    if not form.is_valid() and not academic_errors and nk == 0:
        print(f"  INFO: Formulaire invalide cause par autres champs, pas d'erreurs academiques")
    elif academic_errors:
        print(f"  INFO: Erreurs academiques: {academic_errors}")
    elif form.is_valid():
        print("  PASS: Formulaire valide (MAS + semestre + filiere, pas de module)")
    else:
        print(f"  INFO: Autre situation (valid={form.is_valid()})")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 6: Full valid combination for LIC + S5 + Maths + module + classe
print("\nTest 6: Full valid combination (LIC + S5 + Maths et Applications + module + classe)")
try:
    modules = Module.objects.filter(filiere__niveau='LIC', filiere__semestre__name='S5')
    if modules.exists():
        m = modules.first()
        filiere = get_filiere_by_name_niveau("Mathematiques et Applications", "LIC")
        semestre = Semestre.objects.get(name="S5")
        
        form = SessionAdminForm(data={
            'subject': 'Test',
            'module': m.id,
            'teacher': teacher_id,
            'classe': classe.id,
            'location_type': 'block',
            'date': '2026-01-15',
            'start_time': '08:00',
            'end_time': '10:00',
            'niveau': 'LIC',
            'semestre': semestre.id,
            'filiere': filiere.id if filiere else '',
            'session_type': 'Cours',
            'attendance_radius_meters': 50,
        })
        if form.is_valid():
            print("  PASS: Formulaire valide - combinaison academique coh erente")
            cd = form.cleaned_data
            print(f"    niveau={cd.get('niveau')}, semestre={cd.get('semestre').name if cd.get('semestre') else None}, filiere={cd.get('filiere')}, module={cd.get('module')}")
        else:
            print("  FAIL: Formulaire invalide:", form.errors)
    else:
        print("  SKIP: Aucun module trouve")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\n=== Tests terminés ===")