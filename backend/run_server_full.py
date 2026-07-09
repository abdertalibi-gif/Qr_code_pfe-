#!/usr/bin/env python
"""
Simple test script to verify the fixes and run the Django server
"""
import os
import sys

# Add backend directory to path
backend_dir = "C:\\Users\\Abde\\Desktop\\attendance-system-QR (7)\\attendance-system-QR\\backend"
sys.path.insert(0, backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    print("✓ Django setup successful")
    
    # Test imports
    from users.views import (
        BlockAvailabilityView, 
        RoomAvailabilityView, 
        AmphitheaterAvailabilityView, 
        ScheduleInfoView,
        UserViewSet,
        StudentViewSet,
        ClasseViewSet,
        BlockListView,
        BlockDetailView,
        RoomListView,
        RoomDetailView,
        AmphitheaterListView,
        AmphitheaterDetailView,
        DepartmentListView,
        DepartmentDetailView,
        TeacherListView,
        TeacherImportExcelView,
        DashboardCountsView,
        SystemInfoView,
        admin_statistics,
        app_settings,
        blocks_availability,
        room_availability,
        amphitheater_availability,
        schedule_info,
    )
    print("✓ All view classes imported successfully")
    
    # Test Django management command
    print("\nTesting Django check command...")
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'check'])
    print("✓ Django check passed")
    
    print("\n✅ All tests passed! The application is ready to run.")
    print("\nTo start the Django server, you can:")
    print("1. Use the run server script")
    print("2. Run: python manage.py runserver")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
