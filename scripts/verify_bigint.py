import os

import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

print("-- Verificación PK 'id' con tipo INT --")
q1 = (
    "SELECT TABLE_NAME "
    "FROM information_schema.COLUMNS "
    "WHERE TABLE_SCHEMA = DATABASE() "
    "  AND COLUMN_NAME = 'id' "
    "  AND DATA_TYPE = 'int'"
)
with connection.cursor() as cursor:
    cursor.execute(q1)
    rows = cursor.fetchall()
    if not rows:
        print("OK: No hay PK 'id' con INT.")
    else:
        print("ALERTA: Tablas con PK 'id' INT:")
        for r in rows:
            print(" -", r[0])

print("\n-- Verificación FKs que no son BIGINT --")
q2 = (
    "SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME, c.DATA_TYPE "
    "FROM information_schema.KEY_COLUMN_USAGE kcu "
    "JOIN information_schema.COLUMNS c "
    "  ON c.TABLE_SCHEMA = kcu.TABLE_SCHEMA "
    " AND c.TABLE_NAME = kcu.TABLE_NAME "
    " AND c.COLUMN_NAME = kcu.COLUMN_NAME "
    "WHERE kcu.TABLE_SCHEMA = DATABASE() "
    "  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL "
    "  AND c.DATA_TYPE <> 'bigint'"
)
with connection.cursor() as cursor:
    cursor.execute(q2)
    rows = cursor.fetchall()
    if not rows:
        print("OK: Todas las FKs referenciadas son BIGINT.")
    else:
        print("ALERTA: Columnas FK no BIGINT:")
        for r in rows:
            print(f" - {r[0]}.{r[1]} (tipo {r[2]})")
