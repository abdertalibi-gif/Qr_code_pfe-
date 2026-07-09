#!/usr/bin/env python
import os
import sys

# Add the backend directory to the Python path
backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
sys.path.insert(0, backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'check'])
    print('✓ Django check passed')
except Exception as e:
    print(f'✗ Django check failed: {e}')
    import traceback
    traceback.print_exc()
