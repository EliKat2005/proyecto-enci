# Generated manually to fix errno 150 (FK constraint mismatch)
# Django's built-in app migrations create tables with integer PKs, but DEFAULT_AUTO_FIELD is BigAutoField
# This converts ALL Django base tables to bigint BEFORE contabilidad/core create FKs to them

from django.db import migrations


def drop_all_auth_fks(cursor, db_name):
    """Elimina dinámicamente todos los FKs que apuntan a las tablas auth."""
    # Get all FK constraints
    cursor.execute("""
        SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s
        AND REFERENCED_TABLE_NAME IN ('django_content_type', 'auth_permission', 'auth_group', 'auth_user')
    """, [db_name])

    constraints = cursor.fetchall()
    for table, constraint, _ in constraints:
        try:
            cursor.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{constraint}`")
        except Exception:
            pass  # Ya eliminado o no existe


def readd_all_auth_fks(cursor):
    """Re-agrega los FKs con los nombres que Django espera."""
    fks = [
        ("auth_permission", "content_type_id", "django_content_type", "id", "auth_permission_content_type_id_2f476e4b_fk_django_co"),
        ("django_admin_log", "content_type_id", "django_content_type", "id", "django_admin_log_content_type_id_c4bce8eb_fk_django_co"),
        ("auth_group_permissions", "permission_id", "auth_permission", "id", "auth_group_permissions_permission_id_84c5c92e_fk_auth_perm"),
        ("auth_user_user_permissions", "permission_id", "auth_permission", "id", "auth_user_user_permissions_permission_id_1fbb5f2c_fk_auth_perm"),
        ("auth_group_permissions", "group_id", "auth_group", "id", "auth_group_permissions_group_id_b120cbf9_fk_auth_group_id"),
        ("auth_user_groups", "group_id", "auth_group", "id", "auth_user_groups_group_id_97559544_fk_auth_group_id"),
        ("auth_user_groups", "user_id", "auth_user", "id", "auth_user_groups_user_id_6a12ed8b_fk_auth_user_id"),
        ("auth_user_user_permissions", "user_id", "auth_user", "id", "auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id"),
        ("django_admin_log", "user_id", "auth_user", "id", "django_admin_log_user_id_c564eba6_fk_auth_user_id"),
    ]

    for table, col, ref_table, ref_col, constraint_name in fks:
        try:
            cursor.execute(f"""
                ALTER TABLE `{table}`
                ADD CONSTRAINT `{constraint_name}`
                FOREIGN KEY (`{col}`) REFERENCES `{ref_table}` (`{ref_col}`)
            """)
        except Exception:
            pass  # Ya existe


def check_and_convert_to_bigint(apps, schema_editor):
    """Convierte PKs de integer a bigint."""
    with schema_editor.connection.cursor() as cursor:
        db_name = schema_editor.connection.settings_dict['NAME']

        # 1. Drop all FK constraints
        drop_all_auth_fks(cursor, db_name)

        # 2. Convert all PKs and FKs to bigint
        cursor.execute("ALTER TABLE `django_content_type` MODIFY `id` bigint AUTO_INCREMENT NOT NULL")
        cursor.execute("ALTER TABLE `auth_permission` MODIFY `content_type_id` bigint NOT NULL")
        cursor.execute("ALTER TABLE `django_admin_log` MODIFY `content_type_id` bigint NULL")

        cursor.execute("ALTER TABLE `auth_permission` MODIFY `id` bigint AUTO_INCREMENT NOT NULL")
        cursor.execute("ALTER TABLE `auth_group_permissions` MODIFY `permission_id` bigint NOT NULL")
        cursor.execute("ALTER TABLE `auth_user_user_permissions` MODIFY `permission_id` bigint NOT NULL")

        cursor.execute("ALTER TABLE `auth_group` MODIFY `id` bigint AUTO_INCREMENT NOT NULL")
        cursor.execute("ALTER TABLE `auth_group_permissions` MODIFY `group_id` bigint NOT NULL")
        cursor.execute("ALTER TABLE `auth_user_groups` MODIFY `group_id` bigint NOT NULL")

        cursor.execute("ALTER TABLE `auth_user` MODIFY `id` bigint AUTO_INCREMENT NOT NULL")
        cursor.execute("ALTER TABLE `auth_user_groups` MODIFY `user_id` bigint NOT NULL")
        cursor.execute("ALTER TABLE `auth_user_user_permissions` MODIFY `user_id` bigint NOT NULL")
        cursor.execute("ALTER TABLE `django_admin_log` MODIFY `user_id` bigint NOT NULL")

        # Convertir authtoken_token.user_id si existe (es una app externa)
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'authtoken_token'
        """, [db_name])
        if cursor.fetchone()[0] > 0:
            cursor.execute("ALTER TABLE `authtoken_token` MODIFY `user_id` bigint NOT NULL")

        # 3. Re-add FK constraints
        readd_all_auth_fks(cursor)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('authtoken', '0004_alter_tokenproxy_options'),
    ]

    run_before = [
        ('contabilidad', '0001_initial'),
        ('core', '0001_squashed_0006_migrate_existing_data_to_grupos'),
    ]

    operations = [
        migrations.RunPython(check_and_convert_to_bigint, reverse_code=migrations.RunPython.noop),
    ]
