# Generated manually: add the missing User.department relation.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_add_teacher_fields"),
    ]

    operations = [
        # `Department` est déclaré managed=False : la table n'est pas créée par
        # les migrations normales. Sur une base fraîche (ex. base de test),
        # elle peut donc manquer et la clé étrangère ci-dessous échouerait.
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS departments (
                    id bigserial NOT NULL PRIMARY KEY,
                    name varchar(200) NOT NULL UNIQUE,
                    head_id bigint NULL UNIQUE
                );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddField(
            model_name="user",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="teachers",
                to="users.department",
                verbose_name="Département",
            ),
        ),
    ]
