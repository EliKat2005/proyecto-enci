from django.db import migrations, models


def forwards_copy_empresa(apps, schema_editor):
    Notification = apps.get_model("core", "Notification")
    Empresa = apps.get_model("contabilidad", "Empresa")

    # Copiar empresa_id_legacy -> empresa (si existe)
    ids = list(
        Notification.objects.exclude(empresa_id_legacy=None)
        .values_list("empresa_id_legacy", flat=True)
        .distinct()
    )
    empresa_map = Empresa.objects.in_bulk(ids)

    batch = []
    for note in Notification.objects.exclude(empresa_id_legacy=None).iterator(chunk_size=2000):
        if note.empresa_id_legacy in empresa_map:
            # Asignar por ID evita queries extra
            note.empresa_id = note.empresa_id_legacy
        else:
            note.empresa_id = None
        batch.append(note)
        if len(batch) >= 2000:
            Notification.objects.bulk_update(batch, ["empresa"])
            batch.clear()
    if batch:
        Notification.objects.bulk_update(batch, ["empresa"])


def backwards_copy_empresa(apps, schema_editor):
    Notification = apps.get_model("core", "Notification")

    # Copiar empresa -> empresa_id_legacy
    batch = []
    for note in Notification.objects.exclude(empresa=None).iterator(chunk_size=2000):
        note.empresa_id_legacy = note.empresa_id
        batch.append(note)
        if len(batch) >= 2000:
            Notification.objects.bulk_update(batch, ["empresa_id_legacy"])
            batch.clear()
    if batch:
        Notification.objects.bulk_update(batch, ["empresa_id_legacy"])


class Migration(migrations.Migration):

    dependencies = [
        ("contabilidad", "0017_alter_empresaasiento_numero_asiento"),
        ("core", "0009_userprofile_user"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notification",
            old_name="empresa_id",
            new_name="empresa_id_legacy",
        ),
        migrations.AddField(
            model_name="notification",
            name="empresa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="notifications",
                to="contabilidad.empresa",
            ),
        ),
        migrations.RunPython(forwards_copy_empresa, backwards_copy_empresa),
        migrations.RemoveField(
            model_name="notification",
            name="empresa_id_legacy",
        ),
    ]
