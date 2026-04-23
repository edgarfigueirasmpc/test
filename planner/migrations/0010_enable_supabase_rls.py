from django.db import migrations


PUBLIC_TABLES = [
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
    "auth_user",
    "django_admin_log",
    "django_session",
    "planner_project",
    "planner_project_requested_by",
    "planner_project_assigned_users",
    "planner_projecttask",
    "planner_worklog",
    "planner_worklog_requested_by",
    "planner_worklog_assigned_users",
    "planner_plannersettings",
    "planner_projectattachment",
    "planner_worklogattachment",
]


def set_row_level_security(apps, schema_editor, enabled):
    if schema_editor.connection.vendor != "postgresql":
        return

    action = "ENABLE" if enabled else "DISABLE"
    table_names = "', '".join(PUBLIC_TABLES)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            DO $$
            DECLARE
                table_name text;
            BEGIN
                FOR table_name IN
                    SELECT unnest(ARRAY['{table_names}'])
                LOOP
                    IF to_regclass('public.' || quote_ident(table_name)) IS NOT NULL THEN
                        EXECUTE format(
                            'ALTER TABLE public.%I {action} ROW LEVEL SECURITY',
                            table_name
                        );
                    END IF;
                END LOOP;
            END
            $$;
            """
        )


def enable_row_level_security(apps, schema_editor):
    set_row_level_security(apps, schema_editor, enabled=True)


def disable_row_level_security(apps, schema_editor):
    set_row_level_security(apps, schema_editor, enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0009_projectattachment_worklogattachment"),
    ]

    operations = [
        migrations.RunPython(
            enable_row_level_security,
            reverse_code=disable_row_level_security,
        ),
    ]
