#!/usr/bin/env python
import os
import sys
import subprocess

# Change to backend directory
backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
os.chdir(backend_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

print("Testing Django setup...")
try:
    import django
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

print("\nTesting import of view classes...")
try:
    from users.views import (
        UserViewSet, StudentViewSet, ClasseViewSet,
        BlockAvailabilityView, RoomAvailabilityView, AmphitheaterAvailabilityView,
        ScheduleInfoView
    )
    print("✓ All view classes imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nTesting Django check...")
try:
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'check'])
    print("✓ Django check passed")
except Exception as e:
    print(f"❌ Django check failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\nThe application is ready to run.")
print("To start the server, run:")
print(f"  python {backend_dir}\\_run_django_server.py")
print("\nOr execute the run_django_server.py script directly:")
print("  _run_django_server.py")
print("\nThe server will be accessible at: http://127.0.0.1:8000/")
print("="*60)
