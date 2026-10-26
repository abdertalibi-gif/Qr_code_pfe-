import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from courses.models import Session
from curriculum.models import Filiere, Module, Semestre
print('Sessions count:', Session.objects.count())
if Session.objects.exists():
    s = Session.objects.first()
    print('First session:', s)
    print('  module:', s.module)
    print('  classe:', s.classe)
    if s.classe:
        print('  classe.niveau:', s.classe.niveau)
        print('  classe.filiere:', s.classe.filiere.name if s.classe.filiere else None)
        print('  classe.semestre:', s.classe.semestre.name if s.classe.semestre else None)