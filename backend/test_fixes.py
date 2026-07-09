#!/usr/bin/env python
import os
import subprocess
import time
import signal
import sys

def run_command(cmd, timeout=60):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"

def main():
    print("Testing Django application fixes...")
    
    # Change to backend directory
    backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
    
    # Step 1: Check if Django can start
    print("\n1. Testing Django setup...")
    
    # Check imports at the module level
    try:
        # First check the views module
        import importlib.util
        views_path = f"{backend_dir}\\_users\\views.py"
        spec = importlib.util.spec_from_file_location("users.views", views_path)
        views_module = importlib.util.module_from_spec(spec)
        sys.modules["users.views"] = views_module
        spec.loader.exec_module(views_module)
        print("✓ users/views.py imports successful")
        
        # Check serializers
        serializers_path = f"{backend_dir}\\_users\\serializers.py"
        spec = importlib.util.spec_from_file_location("users.serializers", serializers_path)
        serializers_module = importlib.util.module_from_spec(spec)
        sys.modules["users.serializers"] = serializers_module
        spec.loader.exec_module(serializers_module)
        print("✓ users/serializers.py imports successful")
        
        # Check permissions
        permissions_path = f"{backend_dir}\\_users\\permissions.py"
        spec = importlib.util.spec_from_file_location("users.permissions", permissions_path)
        permissions_module = importlib.util.module_from_spec(spec)
        sys.modules["users.permissions"] = permissions_module
        spec.loader.exec_module(permissions_module)
        print("✓ users/permissions.py imports successful")
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return
    
    # Step 2: Try a simple Django manage.py command
    print("\n2. Testing manage.py commands...")
    
    # Test check command
    code, stdout, stderr = run_command(f"cd {backend_dir} && python manage.py check")
    if code == 0:
        print("✓ django check passed")
    else:
        print(f"✗ django check failed: {stderr}")
    
    # Step 3: Check views exports
    print("\n3. Testing view classes...")
    try:
        from users.views import BlockAvailabilityView, RoomAvailabilityView, AmphitheaterAvailabilityView, ScheduleInfoView
        print("✓ Key view classes imported successfully")
        
        # Check that ModelViewSets are properly defined
        from users.models import Block, Room, Amphitheater
        print("✓ Models imported successfully")
        
        # Check serializers existence
        from users.serializers import BlockSerializer, RoomSerializer, AmphitheaterSerializer
        print("✓ Serializer classes imported successfully")
        
    except Exception as e:
        print(f"✗ View/Serializer import failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
