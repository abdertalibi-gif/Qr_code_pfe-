#!/usr/bin/env python
"""
Test script to verify that all the new classes were added correctly to users/views.py
"""
import os
import sys
import tempfile

# Change to the backend directory
backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
os.chdir(backend_dir)

print("=" * 70)
print("Test Import Script for users/views.py")
print("=" * 70)

# Test importing users.views directly
try:
    print("\n1. Testing direct import of users.views module...")
    
    # Import users.views directly
    import users.views as views_module
    
    print("   ✓ users.views module imported successfully")
    
    # List all public attributes in the module
    public_attrs = [attr for attr in dir(views_module) if not attr.startswith('_')]
    
    print(f"\n   Found {len(public_attrs)} public attributes in users.views:")
    for attr in sorted(public_attrs):
        print(f"     - {attr}")
    
    # Check for the requested classes
    requested_classes = [
        'UserViewSet', 'StudentViewSet', 'ClasseViewSet',
        'admin_statistics', 'amphitheater_detail', 'amphitheater_list',
        'app_settings', 'block_detail', 'block_list',
        'department_list', 'department_detail', 'room_detail',
        'room_list', 'teacher_list', 'teacher_import_excel',
        'dashboard_counts', 'system_info', 'room_availability',
        'amphitheater_availability', 'blocks_availability',
        'schedule_info'
    ]
    
    print(f"\n2. Checking for requested classes...")
    found_classes = []
    missing_classes = []
    
    for class_name in requested_classes:
        if hasattr(views_module, class_name):
            found_classes.append(class_name)
            print(f"   ✓ {class_name} found")
        else:
            missing_classes.append(class_name)
            print(f"   ✗ {class_name} NOT found")
    
    if missing_classes:
        print(f"\n   ❌ MISSING CLASSES: {', '.join(missing_classes)}")
        sys.exit(1)
    else:
        print(f"\n   ✅ All {len(found_classes)} requested classes found!")
    
    # Test the specific imports
    print(f"\n3. Testing imports from users.views...")
    
    # Try to import all the required classes
    from users.views import (
        UserViewSet,
        StudentViewSet,
        ClasseViewSet,
        block_list,
        block_detail,
        room_list,
        room_detail,
        amphitheater_list,
        amphitheater_detail,
        department_list,
        department_detail,
        teacher_list,
        teacher_import_excel,
        dashboard_counts,
        system_info,
        app_settings,
        blocks_availability,
        room_availability,
        amphitheater_availability,
        schedule_info,
        admin_statistics,
    )
    
    print("   ✅ All imports successful!")
    
    print("\n" + "=" * 70)
    print("✅ TEST PASSED!")
    print("=" * 70)
    print("\nThe users/views.py module has been updated successfully with")
    print("all the required classes and functions.")
    print("\nYou can now run the Django server:")
    print(f"  cd {backend_dir}")
    print("  python -c \"import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])\"")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("TEST FAILED!")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
