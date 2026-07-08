import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename='filieres' AND indexname LIKE '%manager%'")
    for r in c.fetchall():
        print(r)
    c.execute("SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'filieres'::regclass")
    for r in c.fetchall():
        print(r)
