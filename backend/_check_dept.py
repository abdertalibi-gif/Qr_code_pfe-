import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from users.models import User
u = User.objects.first()
print('hasattr department:', hasattr(u, 'department'))
try:
    v = getattr(u, 'department', 'NOT_FOUND')
    print('getattr department:', v)
except Exception as e:
    print('getattr error:', e)
