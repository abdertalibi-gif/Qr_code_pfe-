import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_mKh5b0YwsrZJ@ep-proud-hall-ap5q3y9d-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables in PostgreSQL:")
    for t in tables:
        cursor.execute(f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
        cols = cursor.fetchall()
        print(f"\n  {t}:")
        for c in cols:
            print(f"    {c[0]:30s} {c[1]:15s} nullable={c[2]} default={str(c[3])[:40]}")
print("\n--- Done ---")
