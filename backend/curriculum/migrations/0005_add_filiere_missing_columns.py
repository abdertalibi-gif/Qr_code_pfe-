"""Add columns that were faked in migration 0004 via SeparateDatabaseAndState.

These columns already exist in the production (NeonDB) database.
On a fresh test database they must be created conditionally.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0004_filiere_department_filiere_manager"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- filiere.department_id
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='filieres' AND column_name='department_id'
                ) THEN
                    ALTER TABLE filieres ADD COLUMN department_id integer NULL;
                END IF;
                -- filiere.manager_id
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='filieres' AND column_name='manager_id'
                ) THEN
                    ALTER TABLE filieres ADD COLUMN manager_id integer NULL;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
