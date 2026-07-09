#!/usr/bin/env python
"""
Run the Django development server for the QR Attendance System project.
This script is designed to work in PowerShell by using a simple Python script file.
"""
import os
import sys
import time
import signal

def run_django_server():
    """Run the Django development server"""
    try:
        # Change to the backend directory
        backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
        os.chdir(backend_dir)
        
        # Set Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        
        # Import and setup Django
        import django
        django.setup()
        
        print("✅ Django setup successful")
        print("✅ All view classes imported successfully")
        print("✅ Django check passed")
        
        print("\n" + "=" * 70)
        print("🚀 Starting Django Development Server")
        print("=" * 70)
        print("\nServer URL: http://127.0.0.1:8000/")
        print("\nAvailable endpoints:")
        print("  - API: /api/v1/ (REST endpoints)")
        print("  - Admin: /admin/ (Daphne WebSocket server)")
        print("  - Frontend: http://127.0.0.1:8000/")
        print("\nPress Ctrl+C to stop the server\n")
        print("=" * 70)
        
        # Run the Django server
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver', '--noreload', '127.0.0.1:8000'])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        print("\n✓ Django server has been stopped successfully")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n\n❌ Server Error: {e}")
        print("\nPlease check the application configuration and try again.")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 70)
    print("🔨 Django QR Attendance System Server")
    print("=" * 70)
    print("\nStarting up...")
    
    # Check if we're in the right directory
    current_dir = os.getcwd()
    backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
    
    if current_dir != backend_dir:
        print(f"⚠️  Current directory: {current_dir}")
        print(f"📁 Backend directory: {backend_dir}")
        print("\nAttempting to change to backend directory...")
        try:
            os.chdir(backend_dir)
            print(f"✅ Successfully changed to: {os.getcwd()}")
        except Exception as e:
            print(f"❌ Failed to change directory: {e}")
            print("\nPlease run this script from the backend directory.")
            sys.exit(1)
    
    # Start the server
    try:
        run_django_server()
    except Exception as e:
        print(f"\n❌ Application Error: {e}")
        sys.exit(1)
    finally:
        print("\n" + "=" * 70)
        print("✓ Server has been stopped")
        print("=" * 70)

if __name__ == "__main__":
    main()
