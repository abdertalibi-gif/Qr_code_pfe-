import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT conname, contype, conindid 
        FROM pg_constraint 
        WHERE conname LIKE '%unique_classe%' 
        OR conname LIKE '%classe%module%'
        OR conname LIKE '%unique%classe%'
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(r)

    # Also check all constraints on classes table
    cursor.execute("""
        SELECT conname, contype, conindid
        FROM pg_constraint c 
        JOIN pg_class cl ON c.conrelid = cl.oid 
        JOIN pg_namespace n ON cl.relnamespace = n.oid 
        WHERE cl.relname = 'classes'
    """)
    rows = cursor.fetchall()
    print("\n--- All constraints on 'classes' table ---")
    for r in rows:
        print(r)
