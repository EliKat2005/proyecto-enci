from django.conf import settings
from django.db import models
from django.utils import timezone
from django.urls import reverse
import secrets


# --- Clases de Opciones (ENUMs) ---

class TipoCuenta(models.TextChoices):
    ACTIVO = 'Activo', 'Activo'
    PASIVO = 'Pasivo', 'Pasivo'
    PATRIMONIO = 'Patrimonio', 'Patrimonio'
    INGRESO = 'Ingreso', 'Ingreso'
    COSTO = 'Costo', 'Costo'
    GASTO = 'Gasto', 'Gasto'

class NaturalezaCuenta(models.TextChoices):
    DEUDORA = 'Deudora', 'Deudora'
    ACREEDORA = 'Acreedora', 'Acreedora'

class EstadoAsiento(models.TextChoices):
    BORRADOR = 'Borrador', 'Borrador'
    CONFIRMADO = 'Confirmado', 'Confirmado'


# --- Modelos de Tablas ---

class PlanDeCuentas(models.Model):
    """
    Modelo para el Plan de Cuentas.
    Representa la tabla 'contabilidad_plandecuentas'.
    """
    codigo = models.CharField(unique=True, max_length=50)
    descripcion = models.CharField(max_length=255)
    
    tipo = models.CharField(
        max_length=10, 
        choices=TipoCuenta.choices
    )
    naturaleza = models.CharField(
        max_length=9, 
        choices=NaturalezaCuenta.choices
    )
    
    # inspectdb los vio como Integer, los corregimos a BooleanField
    estado_situacion = models.BooleanField(
        db_comment='True si es cuenta de Balance, False si es de Resultado'
    )
    es_auxiliar = models.BooleanField(
        default=False, 
        db_comment='True si es una cuenta hoja (auxiliar) que puede recibir transacciones'
    )
    
    # Relación recursiva (Padre-Hijo)
    padre = models.ForeignKey(
        'self', 
        on_delete=models.PROTECT, # ON DELETE RESTRICT = models.PROTECT en Django
        blank=True, 
        null=True, 
        db_comment='Clave foránea recursiva para la estructura de árbol'
    )

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_plandecuentas'
        verbose_name = 'Plan de Cuenta'
        verbose_name_plural = 'Planes de Cuentas'

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class Asiento(models.Model):
    """
    Modelo para la cabecera del Asiento Contable.
    Representa la tabla 'contabilidad_asiento'.
    """
    fecha = models.DateField()
    descripcion_general = models.TextField()
    
    estado = models.CharField(
        max_length=10, 
        choices=EstadoAsiento.choices, 
        default=EstadoAsiento.BORRADOR
    )
    
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT # ON DELETE RESTRICT
    )
    
    # Hacemos que Django maneje las fechas automáticamente
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_asiento'
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'

    def __str__(self):
        return f"Asiento #{self.id} ({self.fecha}) - {self.descripcion_general[:50]}..."


class Transaccion(models.Model):
    """
    Modelo para el detalle (líneas) del Asiento Contable.
    Representa la tabla 'contabilidad_transaccion'.
    """
    asiento = models.ForeignKey(
        Asiento, 
        on_delete=models.CASCADE # ON DELETE CASCADE
    )
    cuenta = models.ForeignKey(
        PlanDeCuentas, 
        on_delete=models.PROTECT # ON DELETE RESTRICT
    )
    
    detalle_linea = models.CharField(max_length=500, blank=True, null=True)
    parcial = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    debe = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    haber = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_transaccion'
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'

    def __str__(self):
        return f"Línea de Asiento #{self.asiento.id}: {self.cuenta.codigo} | D:{self.debe} H:{self.haber}"


# -------------------------
# Empresas (Proyecto académico: empresas ficticias)
# -------------------------
class Empresa(models.Model):
    """Representa una empresa ficticia creada por un usuario.

    Los profesores pueden crear una empresa "plantilla" y generar un `join_code`
    que los estudiantes usan para importar una copia exacta de la empresa.
    """
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='empresas')
    is_template = models.BooleanField(default=False)
    join_code = models.CharField(max_length=64, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    original = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='copies')
    visible_to_supervisor = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return f"{self.nombre} ({self.owner.username})"

    def generate_join_code(self):
        """Genera y guarda un join_code único para que estudiantes importen/copien la empresa."""
        token = secrets.token_urlsafe(8)
        self.join_code = token
        self.save(update_fields=['join_code'])
        return self.join_code

    @classmethod
    def import_from_template(cls, join_code, new_owner):
        """Busca una empresa template por `join_code` y crea una copia para `new_owner`.

        Retorna la nueva Empresa creada o lanza `Empresa.DoesNotExist` si no existe.
        """
        template = cls.objects.get(join_code=join_code, is_template=True)
        return template.copy_for_owner(new_owner)

    def copy_for_owner(self, new_owner):
        """Crea una copia completa (cuentas, asientos, transacciones) de esta empresa
        asignada a `new_owner`. Devuelve la nueva Empresa.
        """
        # 1) crear la empresa destino
        new_emp = Empresa.objects.create(
            nombre=self.nombre,
            descripcion=self.descripcion,
            owner=new_owner,
            is_template=False,
            original=self,
            visible_to_supervisor=False,  # por defecto off: el estudiante debe habilitarlo
        )

        # 2) copiar cuentas (mantener estructura padre-hijo)
        old_accounts = EmpresaPlanCuenta.objects.filter(empresa=self).order_by('id')
        mapping = {}  # viejo_id -> nuevo_obj
        for acc in old_accounts:
            new_acc = EmpresaPlanCuenta.objects.create(
                empresa=new_emp,
                codigo=acc.codigo,
                descripcion=acc.descripcion,
                tipo=acc.tipo,
                naturaleza=acc.naturaleza,
                estado_situacion=acc.estado_situacion,
                es_auxiliar=acc.es_auxiliar,
                padre=None  # asignaremos padre más tarde
            )
            mapping[acc.id] = new_acc

        # asignar padres ahora que existen todos los nuevos accounts
        for acc in old_accounts:
            if acc.padre_id:
                new_obj = mapping.get(acc.id)
                parent_new = mapping.get(acc.padre_id)
                if new_obj and parent_new:
                    new_obj.padre = parent_new
                    new_obj.save(update_fields=['padre'])

        # 3) copiar asientos y transacciones
        old_asientos = EmpresaAsiento.objects.filter(empresa=self).order_by('id')
        for ast in old_asientos:
            new_ast = EmpresaAsiento.objects.create(
                empresa=new_emp,
                fecha=ast.fecha,
                descripcion_general=ast.descripcion_general,
                estado=ast.estado,
                creado_por=new_owner, # asignamos al estudiante como creador de la copia
            )

            old_lines = EmpresaTransaccion.objects.filter(asiento=ast).order_by('id')
            for ln in old_lines:
                # mapear la cuenta al nuevo account correspondiente por codigo
                new_cuenta = None
                if ln.cuenta and ln.cuenta.codigo:
                    try:
                        new_cuenta = EmpresaPlanCuenta.objects.get(empresa=new_emp, codigo=ln.cuenta.codigo)
                    except EmpresaPlanCuenta.DoesNotExist:
                        new_cuenta = None

                EmpresaTransaccion.objects.create(
                    asiento=new_ast,
                    cuenta=new_cuenta,
                    detalle_linea=ln.detalle_linea,
                    parcial=ln.parcial,
                    debe=ln.debe,
                    haber=ln.haber,
                )

        return new_emp


class EmpresaPlanCuenta(models.Model):
    """Plan de cuentas asociado a una `Empresa` (copia independiente del PlanDeCuentas global)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='cuentas')
    codigo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TipoCuenta.choices)
    naturaleza = models.CharField(max_length=9, choices=NaturalezaCuenta.choices)
    estado_situacion = models.BooleanField()
    es_auxiliar = models.BooleanField(default=False)
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = 'contabilidad_empresa_plandecuentas'
        verbose_name = 'Cuenta (Empresa)'
        verbose_name_plural = 'Cuentas (Empresas)'
        unique_together = ('empresa', 'codigo')

    def __str__(self):
        return f"{self.codigo} - {self.descripcion} [{self.empresa.nombre}]"

    @property
    def level(self):
        """Estima la profundidad estructural de la cuenta según el código.

        Ej: '1' -> 0 (Elemento), '1.1' -> 1 (Grupo), '1.1.01' -> 2 (Subgrupo/Cuenta), etc.
        """
        try:
            return self.codigo.count('.')
        except Exception:
            return 0

    @property
    def structural_type(self):
        """Devuelve una etiqueta estructural basada en la profundidad.

        0 -> Elemento
        1 -> Grupo
        2 -> Subgrupo
        3 -> Cuenta
        >=4 -> Subcuenta
        """
        lvl = self.level
        if lvl <= 0:
            return 'Elemento'
        if lvl == 1:
            return 'Grupo'
        if lvl == 2:
            return 'Subgrupo'
        if lvl == 3:
            return 'Cuenta'
        return 'Subcuenta'

    @property
    def estado_label(self):
        """Etiqueta legible para el campo booleano `estado_situacion`.

        True => 'Balance' (Estado de Situación Financiera)
        False => 'Resultado'
        """
        return 'Balance' if bool(self.estado_situacion) else 'Resultado'


class EmpresaAsiento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='asientos')
    fecha = models.DateField()
    descripcion_general = models.TextField()
    estado = models.CharField(max_length=10, choices=EstadoAsiento.choices, default=EstadoAsiento.BORRADOR)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contabilidad_empresa_asiento'
        verbose_name = 'Asiento (Empresa)'
        verbose_name_plural = 'Asientos (Empresa)'

    def __str__(self):
        return f"Asiento #{self.id} ({self.empresa.nombre}) - {self.descripcion_general[:40]}"


class EmpresaTransaccion(models.Model):
    asiento = models.ForeignKey(EmpresaAsiento, on_delete=models.CASCADE, related_name='lineas')
    cuenta = models.ForeignKey(EmpresaPlanCuenta, on_delete=models.PROTECT, null=True, blank=True)
    detalle_linea = models.CharField(max_length=500, blank=True, null=True)
    parcial = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    debe = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    haber = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'contabilidad_empresa_transaccion'
        verbose_name = 'Transacción (Empresa)'
        verbose_name_plural = 'Transacciones (Empresa)'

    def __str__(self):
        return f"Línea Asiento #{self.asiento.id} [{self.empresa()}]: {self.cuenta.codigo if self.cuenta else 'N/A'} D:{self.debe} H:{self.haber}"

    def empresa(self):
        return self.asiento.empresa.nombre


class EmpresaSupervisor(models.Model):
    """Relaciona una empresa con un docente que la supervisa (por ejemplo, copia creada desde su plantilla).

    Esto permite que los docentes vean las empresas creadas por estudiantes que provienen
    de sus plantillas o cuyo acceso fue concedido al importar con `join_code`.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='supervisores')
    docente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supervisiones')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contabilidad_empresa_supervisor'
        verbose_name = 'Empresa Supervisor'
        verbose_name_plural = 'Empresa Supervisores'
        unique_together = ('empresa', 'docente')

    def __str__(self):
        return f"{self.empresa.nombre} supervisada por {self.docente.username}"


class EmpresaComment(models.Model):
    SECTION_CHOICES = [
        ('PL', 'Plan de Cuentas'),
        ('DI', 'Libro Diario'),
        ('RP', 'Reportes'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='comments')
    section = models.CharField(max_length=2, choices=SECTION_CHOICES)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contabilidad_empresa_comment'
        verbose_name = 'Comentario (Empresa)'
        verbose_name_plural = 'Comentarios (Empresas)'

    def __str__(self):
        return f"Comentario {self.id} en {self.empresa.nombre} - {self.get_section_display()}"