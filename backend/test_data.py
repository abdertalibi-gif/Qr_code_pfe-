import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Filiere, Module, Semestre

print('Semestres:')
for s in Semestre.objects.all():
    print(' ', s.name)

print('\nFilieres:')
for f in Filiere.objects.all():
    print(' ', f.name, '- Niveau:', f.niveau, '- Semestre:', f.semestre.name if f.semestre else 'None')

print('\nModules:')
for m in Module.objects.all():
    print(' ', m.name, '- Filiere:', m.filiere.name if m.filiere else 'None')