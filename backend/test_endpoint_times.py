import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User
from rest_framework_simplejwt.tokens import AccessToken
import urllib.request, json, time

admin = User.objects.filter(role='admin').first()
token = str(AccessToken.for_user(admin))

endpoints = [
    ('/api/v1/classes/', 'Classes'),
    ('/api/v1/curriculum/niveaux/', 'Niveaux'),
    ('/api/v1/curriculum/semestres/', 'Semestres'),
    ('/api/v1/curriculum/filieres/', 'Filieres'),
    ('/api/v1/curriculum/modules/', 'Modules'),
    ('/api/v1/blocks/', 'Blocks'),
    ('/api/v1/amphitheaters/', 'Amphitheaters'),
    ('/api/v1/users/?role=teacher', 'Teachers'),
]

for path, label in endpoints:
    req = urllib.request.Request(f'http://127.0.0.1:8000{path}',
        headers={'Authorization': 'Bearer ' + token})
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        elapsed = time.time() - start
        data = json.loads(resp.read())
        count = len(data) if isinstance(data, list) else data.get('count', '?')
        print(f'{label:15s} {path:45s} -> {resp.status}  count={count}  time={elapsed:.2f}s')
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        print(f'{label:15s} {path:45s} -> {e.code}  time={elapsed:.2f}s  ERROR')
    except Exception as e:
        elapsed = time.time() - start
        print(f'{label:15s} {path:45s} -> TIMEOUT/ERROR  time={elapsed:.2f}s  {type(e).__name__}: {e}')

# Also check the cascade endpoint
print()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/curriculum/semestres-par-niveau/?niveau=LIC',
    headers={'Authorization': 'Bearer ' + token})
start = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=60)
    elapsed = time.time() - start
    data = json.loads(resp.read())
    print(f'{"Cascade":15s} /curriculum/semestres-par-niveau/?niveau=LIC  -> {resp.status}  count={len(data)}  time={elapsed:.2f}s')
except Exception as e:
    elapsed = time.time() - start
    print(f'{"Cascade":15s} /curriculum/semestres-par-niveau/?niveau=LIC  -> ERROR  time={elapsed:.2f}s  {type(e).__name__}: {e}')
