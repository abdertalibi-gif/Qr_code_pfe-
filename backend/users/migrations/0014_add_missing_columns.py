"""Add columns that were faked in migration 0013 via SeparateDatabaseAndState.

These columns already exist in the production (NeonDB) database.
On a fresh test database they must be created conditionally.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_academicyear_department_faculty_group_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- users.is_also_teacher
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='is_also_teacher'
                ) THEN
                    ALTER TABLE users ADD COLUMN is_also_teacher boolean DEFAULT false NOT NULL;
                END IF;
                -- classes.academic_year_ref_id
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='classes' AND column_name='academic_year_ref_id'
                ) THEN
                    ALTER TABLE classes ADD COLUMN academic_year_ref_id integer NULL;
                END IF;
                -- classes.department_id
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='classes' AND column_name='department_id'
                ) THEN
                    ALTER TABLE classes ADD COLUMN department_id integer NULL;
                END IF;
                -- classes.group_id
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='classes' AND column_name='group_id'
                ) THEN
                    ALTER TABLE classes ADD COLUMN group_id integer NULL;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
