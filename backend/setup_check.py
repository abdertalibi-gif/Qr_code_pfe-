#!/usr/bin/env python
import os
import django
def setup_django():
    """Setup Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
if __name__ == '__main__':
    try:
        setup_django()
        print("Django setup successful")
    except Exception as e:
        print(f"Django setup failed: {e}")
        import traceback
        traceback.print_exc()
