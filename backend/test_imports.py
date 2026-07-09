#!/usr/bin/env python
import os
import sys

# Correct path handling
backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"

# Change to backend directory
os.chdir(backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Test imports
print("Testing imports...")

# Test models
from users.models import Block, Room, Amphitheater
print("✓ Models imported")

# Test serializers
from users.serializers import BlockSerializer, RoomSerializer, AmphitheaterSerializer
print("✓ Serializers imported")

# Test permissions
from users.permissions import IsAdmin
print("✓ Permissions imported")

# Test views
from users.views import (
    BlockAvailabilityView, 
    RoomAvailabilityView, 
    AmphitheaterAvailabilityView, 
    ScheduleInfoView
)
print("✓ Views imported")

# Test Django management command
print("\nTesting Django check command...")
from django.core.management import execute_from_command_line

try:
    execute_from_command_line(['manage.py', 'check'])
    print("✓ Django check passed")
except Exception as e:
    print(f"✗ Django check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed! The application is ready to run.")
print("To start the server, run:")
print("  cd {} && python -c \"import django; from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])\"".format(backend_dir))
