# Generated manually to add Kardex to comment choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0024_add_metricas_cache'),
    ]

    operations = [
        migrations.AlterField(
            model_name='empresacomment',
            name='section',
            field=models.CharField(
                choices=[
                    ('PL', 'Plan de Cuentas'),
                    ('DI', 'Libro Diario'),
                    ('MA', 'Libro Mayor'),
                    ('BC', 'Balance de Comprobación'),
                    ('EF', 'Estados Financieros'),
                    ('KD', 'Kardex de Inventario'),
                ],
                max_length=2
            ),
        ),
    ]
