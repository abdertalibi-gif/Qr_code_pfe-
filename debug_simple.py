import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config')

import django
django.setup()

from users.models import User
from curriculum.models import Filiere

# Quick check of database
print("Database connection successful")

# Test 1: Basic counts
print(f"\n=== Basic Counts ===")
print(f"Total Users: {User.objects.count()}")
print(f"Users by role:")
for role in ['admin', 'department_head', 'program_manager', 'teacher', 'student']:
    count = User.objects.filter(role=role).count()
    print(f"  {role}: {count}")

print(f"\nTotal Filiere: {Filiere.objects.count()}")
print(f"Filiere with department: {Filiere.objects.filter(department__isnull=False).count()}")
print(f"Filiere with manager: {Filiere.objects.filter(manager__isnull=False).count()}")

# Test 2: Test direct database queries
print(f"\n=== Direct Query Test ===")

from django.db import connection
import time

# Test unfiltered query
start = time.time()
queryset = Filiere.objects.all()
results = list(queryset)
elapsed = time.time() - start

print(f"Filiere.objects.all(): {len(results)} rows, {elapsed:.3f}s")

# Test with select_related
start = time.time()
queryset = Filiere.objects.select_related('department', 'manager')
results = list(queryset)
elapsed = time.time() - start

print(f"Filiere.objects.select_related(): {len(results)} rows, {elapsed:.3f}s")

# Test with order_by
start = time.time()
queryset = Filiere.objects.select_related('department', 'manager').order_by('name')
results = list(queryset)
elapsed = time.time() - start

print(f"Filiere.objects.order_by(): {len(results)} rows, {elapsed:.3f}s")

# Get SQL and EXPLAIN
print(f"\n=== SQL Query Analysis ===")

# Get all unique SQL queries and execution times
import re
from django.db import connection

# Force query logging
print("Checking database configuration...")
print(f"Database engine: {connection.settings_dict['ENGINE']}")

# Check if select_related is efficient
from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT * FROM filieres LIMIT 5;")
rows = cursor.fetchall()
print(f"Sample filieres: {len(rows)} rows")
if rows:
    print(f"First filiere: {rows[0]}")
    print(f"Columns: {[col[0] for col in cursor.description]}")