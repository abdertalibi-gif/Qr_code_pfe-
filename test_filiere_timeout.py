import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config')

import django
django.setup()

from django.test import RequestFactory
from curriculum.views import filiere_list
from users.models import User
from django.core.management import execute_from_command_line
from django.core.management import call_command

print("Testing filiere_list with bypass authentication")
print("=" * 60)

factory = RequestFactory()

# Get first available user - try different approaches
try:
    # Try to get any user
    user = User.objects.first()
    print(f"Using user: {user.email} (role: {user.role})")
    
    request = factory.get('/api/v1/curriculum/filieres/')
    request.user = user
    
    # Directly call the view
    response = filiere_list(request)
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if hasattr(response, 'data'):
        data = response.data
        if isinstance(data, list):
            print(f"Number of filieres: {len(data)}")
            if len(data) > 0:
                print(f"First filiere: {data[0]}")
        else:
            print(f"Data type: {type(data)}")
            print(f"Data: {data}")
    
    # Check response time
    import time
    start = time.time()
    
    # Try again to see performance
    request2 = factory.get('/api/v1/curriculum/filieres/')
    request2.user = user
    response2 = filiere_list(request2)
    elapsed = time.time() - start
    
    print(f"Second request elapsed: {elapsed:.3f}s")
    print(f"Total filieres: {len(response2.data) if isinstance(response2.data, list) else 'not list'}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Testing direct database query")

from curriculum.models import Filiere

# Get a simple count
start = time.time()
queryset = Filiere.objects.select_related('department', 'manager').order_by('name')
elapsed = time.time() - start

print(f"Direct queryset count: {queryset.count()}, elapsed: {elapsed:.3f}s")

# Test the queryset directly
start = time.time()
queryset_all = Filiere.objects.all()
elapsed = time.time() - start

print(f"Unfiltered queryset count: {queryset_all.count()}, elapsed: {elapsed:.3f}s")

# Test select_related version
start = time.time()
queryset_select = Filiere.objects.select_related('department', 'manager', 'semestre')
elapsed = time.time() - start

print(f"select_related queryset count: {queryset_select.count()}, elapsed: {elapsed:.3f}s")