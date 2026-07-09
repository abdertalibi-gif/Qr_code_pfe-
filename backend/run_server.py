#!/usr/bin/env python
import os
import django
import sys

def setup_django():
    """Setup Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

if __name__ == '__main__':
    try:
        setup_django()
        print("Django setup successful")
        
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])
    except KeyboardInterrupt:
        print('Server stopped')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
