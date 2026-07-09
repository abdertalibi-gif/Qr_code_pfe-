#!/usr/bin/env python
"""
Simple script to run the Django QR Attendance System project.
This script is designed to work on Windows with a simpler approach.
"""
import os
import sys

def main():
    # Simple approach: change to backend directory and run Django
    backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
    
    # Change to the backend directory
    print(f"Changing to directory: {backend_dir}")
    os.chdir(backend_dir)
    
    print(f"Current directory: {os.getcwd()}")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    print("✓ Environment variable set")
    
    # Import Django
    try:
        import django
        django.setup()
        print("✓ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        sys.exit(1)
    
    # Test imports
    print("\nTesting imports...")
    try:
        from users.views import (
            UserViewSet, StudentViewSet, ClasseViewSet,
            BlockAvailabilityView, RoomAvailabilityView, AmphitheaterAvailabilityView,
            ScheduleInfoView
        )
        print("✓ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)
    
    # Run Django management command
    print("\nRunning Django management command...")
    try:
        from django.core.management import execute_from_command_line
        
        print("Starting Django server on http://127.0.0.1:8000")
        print("Press Ctrl+C to stop the server\n")
        
        # Run the server
        execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])
        
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped successfully")
    except Exception as e:
        print(f"\n❌ Server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
