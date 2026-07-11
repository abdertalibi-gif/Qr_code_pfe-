"""Check if classes have modules assigned and if sessions' modules match."""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from courses.models import Session
from users.models import Student, Classe

# Check classes with module FK set
total_classes = Classe.objects.count()
classes_with_module = Classe.objects.filter(module__isnull=False).count()
print(f"Classes total: {total_classes}")
print(f"Classes with module FK set: {classes_with_module}")

# Check the 10 most recent sessions
for s in Session.objects.order_by('-id').select_related('classe', 'module')[:10]:
    print(f"Session {s.id}: classe_id={s.classe_id} (module_in_class={s.classe.module_id}), module_id={s.module_id}")
    class_mod_matches = s.classe.module_id == s.module_id
    print(f"  Classe.module matches session.module: {class_mod_matches}")

# Check if any student has module_enrollment for a session's module
print("\nChecking module enrollments:")
for s in Session.objects.filter(module__isnull=False).select_related('classe')[:5]:
    enrolled = Student.objects.filter(classe_id=s.classe_id, modules=s.module).count()
    class_mod = Student.objects.filter(classe_id=s.classe_id, classe__module_id=s.module_id).count()
    print(f"Session {s.id} (module={s.module_id}): students_enrolled_in_module={enrolled}, students_with_class_module_match={class_mod}")
