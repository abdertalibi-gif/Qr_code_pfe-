import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from users.models import User
from curriculum.models import Filiere, Module, Semestre
from django.db.models import Q

def test():
    try:
        print("Testing dept_teacher_ids query...")
        dept_id = 1
        dept_teacher_ids = User.objects.filter(
            Q(role="teacher")
            & (Q(assigned_classes__department_id=dept_id)
               | Q(assigned_classes__filiere__department_id=dept_id)
               | Q(sessions__classe__department_id=dept_id)
               | Q(sessions__classe__filiere__department_id=dept_id)
               | Q(taught_modules__filiere__department_id=dept_id))
        ).values_list("id", flat=True).distinct()
        print("Result:", list(dept_teacher_ids))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
