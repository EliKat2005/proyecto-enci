from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from core.models import UserProfile


class Command(BaseCommand):
    help = 'Crear el grupo "docente" y asignar permisos para gestionar perfiles de estudiantes'

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name="docente")
        if created:
            self.stdout.write(self.style.SUCCESS('Grupo "docente" creado.'))
        else:
            self.stdout.write('Grupo "docente" ya existe.')

        # Intentamos asignar el permiso change_userprofile
        try:
            ct = ContentType.objects.get_for_model(UserProfile)
            perm = Permission.objects.get(codename="change_userprofile", content_type=ct)
            group.permissions.add(perm)
            self.stdout.write(
                self.style.SUCCESS('Permiso "change_userprofile" asignado al grupo "docente".')
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"No se pudo asignar permiso: {e}"))

        self.stdout.write(self.style.SUCCESS("Operación finalizada."))
