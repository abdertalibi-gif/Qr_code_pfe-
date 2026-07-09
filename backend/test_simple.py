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
    
    print("\n✅ All imports successful! Application ready.")
    print("Backend directory: {}".format(backend_dir))
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
