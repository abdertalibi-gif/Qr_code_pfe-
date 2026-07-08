import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("ALTER TABLE filieres DROP CONSTRAINT IF EXISTS filieres_manager_id_key")
    print("Dropped UNIQUE constraint filieres_manager_id_key")
    c.execute("CREATE INDEX IF NOT EXISTS idx_filieres_manager ON filieres(manager_id)")
    print("Created non-unique index idx_filieres_manager")
