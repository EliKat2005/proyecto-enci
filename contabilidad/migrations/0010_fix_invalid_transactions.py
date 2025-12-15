# Generated migration file

from django.db import migrations


def fix_transactions_with_both_positive(apps, schema_editor):
    """
    Corrige transacciones que tienen tanto debe como haber > 0.
    
    Estas transacciones violan las reglas contables de partida doble.
    La solución es dividirlas en dos líneas separadas: una para debe y otra para haber.
    
    Nota: Esta migración puede ser saltada si la tabla no existe (por ej. en nuevas instalaciones).
    """
    try:
        EmpresaTransaccion = apps.get_model('contabilidad', 'EmpresaTransaccion')
    except LookupError:
        # Tabla no existe, no hay nada que corregir
        return
    
    # Buscar transacciones inválidas
    violaciones = EmpresaTransaccion.objects.filter(debe__gt=0, haber__gt=0)
    
    for transaccion in violaciones:
        # Crear dos líneas separadas
        # 1. Línea en el debe
        EmpresaTransaccion.objects.create(
            asiento=transaccion.asiento,
            cuenta=transaccion.cuenta,
            detalle_linea=f"{transaccion.detalle_linea or ''} (Debe - corregido)",
            debe=transaccion.debe,
            haber=0
        )
        
        # 2. Línea en el haber
        EmpresaTransaccion.objects.create(
            asiento=transaccion.asiento,
            cuenta=transaccion.cuenta,
            detalle_linea=f"{transaccion.detalle_linea or ''} (Haber - corregido)",
            debe=0,
            haber=transaccion.haber
        )
        
        # Eliminar la transacción inválida original
        transaccion.delete()


class Migration(migrations.Migration):
    """
    Migración de datos para corregir transacciones inválidas
    antes de aplicar CHECK constraints.
    """

    dependencies = [
        ('contabilidad', '0009_alter_asiento_options_alter_plandecuentas_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            fix_transactions_with_both_positive,
            reverse_code=migrations.RunPython.noop
        ),
    ]
