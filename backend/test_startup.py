#!/usr/bin/env python
"""
Run the Django development server.
This script fixes the PowerShell quoting issues by using proper escaping.
"""
import os
import sys

def main():
    # Change to backend directory
    backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
    os.chdir(backend_dir)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Import and setup Django
    try:
        import django
        django.setup()
        print("✅ Django setup successful")
        
        # Test critical imports
        from users.views import UserViewSet, StudentViewSet, ClasseViewSet
        print("✅ View classes imported successfully")
        
        # Test Django management command
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'check'])
        print("✅ Django check passed")
        
        print("\n🎉 All tests passed!")
        print("To run the server, execute:")
        print("python run_server_command.py")
        print("\nOr start it manually with:")
        print(f"cd {backend_dir}")
        print("python -c \\"import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])\\\"")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
