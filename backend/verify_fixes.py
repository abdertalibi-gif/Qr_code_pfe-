#!/usr/bin/env python
import os
import sys
import importlib.util

def test_imports():
    """Test all the critical imports to ensure they work"""
    print("Testing critical imports...")
    
    # Test views module
    try:
        views_path = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend\\users\\views.py"
        spec = importlib.util.spec_from_file_location("users.views", views_path)
        views_module = importlib.util.module_from_spec(spec)
        sys.modules["users.views"] = views_module
        spec.loader.exec_module(views_module)
        print("✓ users/views.py imports successful")
    except Exception as e:
        print(f"✗ users/views.py import failed: {e}")
        return False
    
    # Test serializers module
    try:
        serializers_path = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend\\users\\serializers.py"
        spec = importlib.util.spec_from_file_location("users.serializers", serializers_path)
        serializers_module = importlib.util.module_from_spec(spec)
        sys.modules["users.serializers"] = serializers_module
        spec.loader.exec_module(serializers_module)
        print("✓ users/serializers.py imports successful")
    except Exception as e:
        print(f"✗ users/serializers.py import failed: {e}")
        return False
    
    # Test permissions module
    try:
        permissions_path = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend\\users\\permissions.py"
        spec = importlib.util.spec_from_file_location("users.permissions", permissions_path)
        permissions_module = importlib.util.module_from_spec(spec)
        sys.modules["users.permissions"] = permissions_module
        spec.loader.exec_module(permissions_module)
        print("✓ users/permissions.py imports successful")
    except Exception as e:
        print(f"✗ users/permissions.py import failed: {e}")
        return False
    
    return True

def test_django_setup():
    """Test Django setup"""
    print("\nTesting Django setup...")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        import django
        django.setup()
        print("✓ Django setup successful")
        return True
    except Exception as e:
        print(f"✗ Django setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manage_command():
    """Test a simple Django management command"""
    print("\nTesting Django management commands...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Test check command
        print("Running: check")
        execute_from_command_line(['manage.py', 'check'])
        print("✓ Django check passed")
        return True
    except Exception as e:
        print(f"✗ Django check failed: {e}")
        return False

def test_views_availability():
    """Test that view classes are available"""
    print("\nTesting view class availability...")
    
    try:
        # Import after Django setup
        from users.views import (
            BlockAvailabilityView, 
            RoomAvailabilityView, 
            AmphitheaterAvailabilityView, 
            ScheduleInfoView
        )
        print("✓ View classes imported successfully")
        
        # Verify models exist
        from users.models import Block, Room, Amphitheater
        print("✓ Required models imported")
        
        return True
    except Exception as e:
        print(f"✗ View availability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Django Application Fix Verification")
    print("=" * 60)
    
    all_passed = True
    
    # Run all tests
    all_passed &= test_imports()
    
    if all_passed:
        all_passed &= test_django_setup()
    
    if all_passed:
        all_passed &= test_manage_command()
    
    if all_passed:
        all_passed &= test_views_availability()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED! The application is ready to run.")
    else:
        print("❌ SOME TESTS FAILED. Please fix the issues above.")
    print("=" * 60)
