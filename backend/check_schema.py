import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_mKh5b0YwsrZJ@ep-proud-hall-ap5q3y9d-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.db import connection

with connection.cursor() as cursor:
    # Check if is_also_teacher column exists in users
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_also_teacher'")
    has_col = cursor.fetchone()
    print(f"users.is_also_teacher exists: {has_col is not None}")
    
    # Check if department_id exists in filieres
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='filieres' AND column_name='department_id'")
    has_col = cursor.fetchone()
    print(f"filieres.department_id exists: {has_col is not None}")
    
    # Check if manager_id exists in filieres
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='filieres' AND column_name='manager_id'")
    has_col = cursor.fetchone()
    print(f"filieres.manager_id exists: {has_col is not None}")
    
    # Check if departments table exists
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='departments'")
    has_table = cursor.fetchone()
    print(f"departments table exists: {has_table is not None}")
    
    # Check if is_also_teacher exists in users (from DB schema) 
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' AND column_name='is_also_teacher'")
    col = cursor.fetchone()
    if col:
        print(f"  is_also_teacher: type={col[1]}")
    
    # Check existing role constraint
    cursor.execute("SELECT oid, typname, typcategory FROM pg_type WHERE typname='varchar'")
    
    # Check actual role values
    cursor.execute("SELECT DISTINCT role FROM users ORDER BY role")
    roles = [r[0] for r in cursor.fetchall()]
    print(f"Existing roles: {roles}")
