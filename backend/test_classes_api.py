"""
Test script for Classes API
Run with: python test_classes_api.py
"""
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from users.models import User, Classe, Block, Room
from curriculum.models import Filiere, Semestre

def test_classes_api():
    print("=== Testing Classes API ===\n")
    
    # Get or create test user
    admin_user = User.objects.filter(role="admin").first()
    if not admin_user:
        admin_user = User.objects.create_superuser(
            email="admin@test.com",
            password="admin123",
            first_name="Admin",
            last_name="User"
        )
        admin_user.role = "admin"
        admin_user.is_staff = True
        admin_user.save()
    
    # Set a known password for testing
    admin_user.set_password("admin123")
    admin_user.save()
    
    # Create test data
    semestre, _ = Semestre.objects.get_or_create(name="S1")
    filiere, _ = Filiere.objects.get_or_create(
        name="Test Filiere",
        semestre=semestre,
        niveau="LIC"
    )
    block, _ = Block.objects.get_or_create(name="Block A")
    room, _ = Room.objects.get_or_create(block=block, name="Room 101")
    
    client = APIClient()
    # Login
    response = client.post('/api/v1/auth/login/', {
        'email': admin_user.email,
        'password': 'admin123'
    })
    print(f"Login response: {response.status_code}")
    if response.status_code == 200:
        token = response.json()['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    else:
        print("Login failed!")
        return
    
    # Test GET /api/v1/classes/
    print("\n1. Testing GET /api/v1/classes/")
    response = client.get('/api/v1/classes/')
    print(f"   Status: {response.status_code}")
    print(f"   Count: {len(response.json()) if response.status_code == 200 else 'N/A'}")
    
    # Test POST /api/v1/classes/
    print("\n2. Testing POST /api/v1/classes/")
    classe_data = {
        "niveau_id": "LIC",
        "filiere_id": filiere.id,
        "semestre_id": semestre.id,
        "academic_year": "2025-2026",
        "location_type": "BLOC",
        "block_id": block.id,
        "room_id": room.id,
    }
    response = client.post('/api/v1/classes/', classe_data, format='json')
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        print(f"   Created: {response.json()}")
        classe_id = response.json()['id']
    else:
        print(f"   Error: {response.json() if response.status_code != 500 else '500 Internal Server Error'}")
        classe_id = None
    
    if classe_id:
        # Test GET /api/v1/classes/{id}/
        print(f"\n3. Testing GET /api/v1/classes/{classe_id}/")
        response = client.get(f'/api/v1/classes/{classe_id}/')
        print(f"   Status: {response.status_code}")
        print(f"   Data: {response.json() if response.status_code == 200 else 'N/A'}")
        
        # Test PUT /api/v1/classes/{id}/
        print(f"\n4. Testing PUT /api/v1/classes/{classe_id}/")
        update_data = {
            "niveau_id": "LIC",
            "filiere_id": filiere.id,
            "semestre_id": semestre.id,
            "academic_year": "2025-2026",
            "location_type": "BLOC",
            "block_id": block.id,
            "room_id": room.id,
        }
        response = client.put(f'/api/v1/classes/{classe_id}/', update_data, format='json')
        print(f"   Status: {response.status_code}")
        print(f"   Data: {response.json() if response.status_code == 200 else 'N/A'}")
        
        # Test DELETE /api/v1/classes/{id}/
        print(f"\n5. Testing DELETE /api/v1/classes/{classe_id}/")
        response = client.delete(f'/api/v1/classes/{classe_id}/')
        print(f"   Status: {response.status_code}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_classes_api()
