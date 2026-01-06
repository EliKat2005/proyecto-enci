from django.db import connection, migrations


def convert_int_pk_fk_to_bigint(apps, schema_editor):
    """
    Convert all INT primary keys named 'id' and all referencing foreign keys
    to BIGINT to align with DEFAULT_AUTO_FIELD = BigAutoField.

    Steps for each affected table:
      1) Drop foreign keys referencing <table>.id
      2) Alter parent PK column to BIGINT AUTO_INCREMENT
      3) Alter child FK columns to BIGINT preserving NULLability
      4) Recreate foreign keys with original ON DELETE/UPDATE rules

    This operates across the current MySQL schema and is safe to re-run: if a
    column is already BIGINT it will be skipped.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        schema = cursor.fetchone()[0]

        # Find tables whose PK 'id' is INT (not BIGINT)
        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND COLUMN_NAME = 'id'
              AND DATA_TYPE = 'int'
            """,
            [schema],
        )
        int_pk_tables = [row[0] for row in cursor.fetchall()]

        if not int_pk_tables:
            # Nothing to do
            return

        for table in int_pk_tables:
            # Collect FKs referencing this table.id
            cursor.execute(
                """
                SELECT kcu.TABLE_NAME AS child_table,
                       kcu.CONSTRAINT_NAME,
                       kcu.COLUMN_NAME,
                       rc.DELETE_RULE,
                       rc.UPDATE_RULE
                FROM information_schema.KEY_COLUMN_USAGE kcu
                JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
                 AND rc.CONSTRAINT_NAME   = kcu.CONSTRAINT_NAME
                WHERE kcu.TABLE_SCHEMA = %s
                  AND kcu.REFERENCED_TABLE_NAME = %s
                  AND kcu.REFERENCED_COLUMN_NAME = 'id'
                ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME
                """,
                [schema, table],
            )
            fks = cursor.fetchall()

            # Drop FK constraints on child tables first
            for child_table, constraint_name, column_name, delete_rule, update_rule in fks:
                cursor.execute(
                    f"ALTER TABLE `{child_table}` DROP FOREIGN KEY `{constraint_name}`"
                )

            # Alter parent PK to BIGINT AUTO_INCREMENT
            cursor.execute(
                f"ALTER TABLE `{table}` MODIFY COLUMN `id` BIGINT NOT NULL AUTO_INCREMENT"
            )

            # Alter child FK columns to BIGINT and recreate FKs
            for child_table, constraint_name, column_name, delete_rule, update_rule in fks:
                # Get NULLability of the child column to preserve it
                cursor.execute(
                    """
                    SELECT IS_NULLABLE
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                    """,
                    [schema, child_table, column_name],
                )
                nullable = cursor.fetchone()[0]  # 'YES' or 'NO'
                null_sql = "NULL" if nullable == "YES" else "NOT NULL"

                cursor.execute(
                    f"ALTER TABLE `{child_table}` MODIFY COLUMN `{column_name}` BIGINT {null_sql}"
                )

                # Recreate the FK with original rules
                # Map rules to SQL (CASCADE/SET NULL/RESTRICT/NO ACTION)
                delete_sql = f" ON DELETE {delete_rule}" if delete_rule else ""
                update_sql = f" ON UPDATE {update_rule}" if update_rule else ""

                cursor.execute(
                    f"ALTER TABLE `{child_table}`\n"
                    f"  ADD CONSTRAINT `{constraint_name}`\n"
                    f"  FOREIGN KEY (`{column_name}`) REFERENCES `{table}`(`id`){delete_sql}{update_sql}"
                )


class Migration(migrations.Migration):
    # Non-atomic: MySQL may not allow some DDL inside a single transaction
    atomic = False

    dependencies = [
        ('contabilidad', '0015_empresatercero_delete_asiento_delete_transaccion_and_more'),
        ('core', '0006_migrate_existing_data_to_grupos'),
    ]

    operations = [
        migrations.RunPython(convert_int_pk_fk_to_bigint, migrations.RunPython.noop),
    ]
