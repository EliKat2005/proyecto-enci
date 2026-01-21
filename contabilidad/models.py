import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

# --- Clases de Opciones (ENUMs) ---


class TipoCuenta(models.TextChoices):
    ACTIVO = "Activo", "Activo"
    PASIVO = "Pasivo", "Pasivo"
    PATRIMONIO = "Patrimonio", "Patrimonio"
    INGRESO = "Ingreso", "Ingreso"
    COSTO = "Costo", "Costo"
    GASTO = "Gasto", "Gasto"


class NaturalezaCuenta(models.TextChoices):
    DEUDORA = "Deudora", "Deudora"
    ACREEDORA = "Acreedora", "Acreedora"


class EstadoAsiento(models.TextChoices):
    BORRADOR = "Borrador", "Borrador"
    CONFIRMADO = "Confirmado", "Confirmado"
    ANULADO = "Anulado", "Anulado"  # Para soft-delete


# --- Modelos de Tablas ---


class PlanDeCuentas(models.Model):
    """
    Modelo para el Plan de Cuentas.
    Representa la tabla 'contabilidad_plandecuentas'.
    """

    codigo = models.CharField(unique=True, max_length=50)
    descripcion = models.CharField(max_length=255)

    tipo = models.CharField(max_length=10, choices=TipoCuenta.choices)
    naturaleza = models.CharField(max_length=9, choices=NaturalezaCuenta.choices)

    # inspectdb los vio como Integer, los corregimos a BooleanField
    es_auxiliar = models.BooleanField(
        default=False,
        db_comment="True si es una cuenta hoja (auxiliar) que puede recibir transacciones",
    )

    # Relación recursiva (Padre-Hijo)
    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,  # ON DELETE RESTRICT = models.PROTECT en Django
        blank=True,
        null=True,
        db_comment="Clave foránea recursiva para la estructura de árbol",
    )

    class Meta:
        managed = False  # Tabla legacy no utilizada (se usa EmpresaPlanCuenta)
        db_table = "contabilidad_plandecuentas"
        verbose_name = "Plan de Cuenta"
        verbose_name_plural = "Planes de Cuentas"

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


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
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    eslogan = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="empresas", db_constraint=False
    )
    is_template = models.BooleanField(default=False)
    join_code = models.CharField(max_length=64, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    original = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="copies"
    )
    visible_to_supervisor = models.BooleanField(default=True)

    class Meta:
        db_table = "contabilidad_empresa"
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.nombre} ({self.owner.username})"

    def generate_join_code(self):
        """Genera y guarda un join_code único para que estudiantes importen/copien la empresa."""
        token = secrets.token_urlsafe(8)
        self.join_code = token
        self.save(update_fields=["join_code"])
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
        with transaction.atomic():
            # 1) crear la empresa destino
            new_emp = Empresa.objects.create(
                nombre=self.nombre,
                descripcion=self.descripcion,
                logo=self.logo,
                eslogan=self.eslogan,
                owner=new_owner,
                is_template=False,
                original=self,
                visible_to_supervisor=False,  # por defecto off: el estudiante debe habilitarlo
            )

            # 2) copiar cuentas (mantener estructura padre-hijo) evitando N+1
            old_accounts = list(EmpresaPlanCuenta.objects.filter(empresa=self).order_by("id"))
            new_accounts = [
                EmpresaPlanCuenta(
                    empresa=new_emp,
                    codigo=acc.codigo,
                    descripcion=acc.descripcion,
                    tipo=acc.tipo,
                    naturaleza=acc.naturaleza,
                    es_auxiliar=acc.es_auxiliar,
                    activa=acc.activa,
                    padre=None,
                )
                for acc in old_accounts
            ]
            EmpresaPlanCuenta.objects.bulk_create(new_accounts, batch_size=1000)

            mapping = {old.id: new for old, new in zip(old_accounts, new_accounts, strict=True)}
            codigo_to_new = {acc.codigo: acc for acc in new_accounts}

            to_update = []
            for old in old_accounts:
                if old.padre_id:
                    new_obj = mapping.get(old.id)
                    parent_new = mapping.get(old.padre_id)
                    if new_obj and parent_new:
                        new_obj.padre = parent_new
                        to_update.append(new_obj)

            if to_update:
                EmpresaPlanCuenta.objects.bulk_update(to_update, ["padre"], batch_size=1000)

            # 3) copiar asientos y transacciones (prefetch + bulk_create por asiento)
            old_asientos = (
                EmpresaAsiento.objects.filter(empresa=self)
                .prefetch_related("lineas", "lineas__cuenta")
                .order_by("id")
            )

            for ast in old_asientos:
                new_ast = EmpresaAsiento.objects.create(
                    empresa=new_emp,
                    fecha=ast.fecha,
                    descripcion_general=ast.descripcion_general,
                    estado=ast.estado,
                    creado_por=new_owner,
                    anulado=ast.anulado,
                )

                transacciones = []
                for ln in ast.lineas.all():
                    new_cuenta = None
                    if ln.cuenta_id:
                        new_cuenta = codigo_to_new.get(ln.cuenta.codigo)

                    transacciones.append(
                        EmpresaTransaccion(
                            asiento=new_ast,
                            cuenta=new_cuenta,
                            detalle_linea=ln.detalle_linea,
                            debe=ln.debe,
                            haber=ln.haber,
                            creado_por=new_owner,
                        )
                    )

                if transacciones:
                    EmpresaTransaccion.objects.bulk_create(transacciones, batch_size=2000)

            return new_emp


class EmpresaPlanCuenta(models.Model):
    """Plan de cuentas asociado a una `Empresa` (copia independiente del PlanDeCuentas global)."""

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="cuentas", db_index=True
    )
    codigo = models.CharField(max_length=50, db_index=True)
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TipoCuenta.choices, db_index=True)
    naturaleza = models.CharField(max_length=9, choices=NaturalezaCuenta.choices)
    es_auxiliar = models.BooleanField(
        default=False,
        help_text="True si es una cuenta transaccional (hoja) que puede recibir movimientos",
    )
    activa = models.BooleanField(
        default=True, help_text="True si la cuenta está activa y puede recibir transacciones"
    )
    padre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="hijas"
    )

    class Meta:
        db_table = "contabilidad_empresa_plandecuentas"
        verbose_name = "Cuenta (Empresa)"
        verbose_name_plural = "Cuentas (Empresas)"
        unique_together = ("empresa", "codigo")
        indexes = [
            models.Index(fields=["empresa", "codigo"]),
            models.Index(fields=["empresa", "tipo"]),
            models.Index(fields=["empresa", "es_auxiliar"]),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.descripcion} [{self.empresa.nombre}]"

    def clean(self):
        """Validaciones de modelo."""
        super().clean()

        # Validar que el código siga una estructura lógica
        if self.codigo:
            partes = self.codigo.split(".")
            # Validar formato según nivel
            for parte in partes:
                if not parte.strip():
                    raise ValidationError(
                        {"codigo": "El código no puede contener puntos consecutivos o vacíos."}
                    )

        # Validar que si tiene padre, el código debe comenzar con el código del padre
        if self.padre:
            if not self.codigo.startswith(self.padre.codigo):
                raise ValidationError(
                    {
                        "codigo": f"El código debe comenzar con el código del padre ({self.padre.codigo})."
                    }
                )

            # Heredar tipo y naturaleza del padre si no están definidos
            if not self.tipo:
                self.tipo = self.padre.tipo
            if not self.naturaleza:
                self.naturaleza = self.padre.naturaleza

            # Evitar ciclos padre-hijo (A -> B -> A)
            ancestro = self.padre
            while ancestro:
                if ancestro == self or (self.pk and ancestro.pk == self.pk):
                    raise ValidationError(
                        {"padre": "Asignar este padre genera un ciclo en el plan de cuentas."}
                    )
                ancestro = ancestro.padre

        # Validar jerarquía: cuentas con hijas no pueden ser transaccionales
        # Evitar acceso a relaciones antes de tener PK
        if self.es_auxiliar and self.pk:
            if self.hijas.exists():
                raise ValidationError(
                    {
                        "es_auxiliar": "Las cuentas que tienen subcuentas no pueden ser marcadas como transaccionales."
                    }
                )

        # No permitir agregar hijas a una cuenta transaccional
        if self.padre and self.padre.es_auxiliar:
            raise ValidationError(
                {"padre": "No se puede agregar subcuentas a una cuenta transaccional."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def tiene_hijas(self):
        """Retorna True si esta cuenta tiene subcuentas."""
        return self.hijas.exists()

    @property
    def puede_recibir_transacciones(self):
        """Solo las cuentas transaccionales (hojas del árbol) activas pueden recibir movimientos."""
        return self.es_auxiliar and not self.tiene_hijas and self.activa

    @property
    def level(self):
        """Estima la profundidad estructural de la cuenta según el código.

        Ej: '1' -> 0 (Elemento), '1.1' -> 1 (Grupo), '1.1.01' -> 2 (Subgrupo/Cuenta), etc.
        """
        try:
            return self.codigo.count(".")
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
            return "Elemento"
        if lvl == 1:
            return "Grupo"
        if lvl == 2:
            return "Subgrupo"
        if lvl == 3:
            return "Cuenta"
        return "Subcuenta"

    def get_grupo_principal(self):
        """Retorna el primer ancestro NO auxiliar (grupo principal).
        
        Si la cuenta actual no es auxiliar, se retorna a sí misma.
        Si no tiene padre, retorna a sí misma.
        """
        if not self.es_auxiliar:
            return self
        
        ancestro = self.padre
        while ancestro:
            if not ancestro.es_auxiliar:
                return ancestro
            ancestro = ancestro.padre
        
        # Si no hay padre no auxiliar, retornar la propia cuenta
        return self


class EmpresaTercero(models.Model):
    """
    Modelo para normalizar beneficiarios (Clientes, Proveedores, Empleados, Accionistas, Gobierno).

    Permite reportes fiscales por tercero (Libro Auxiliar por Tercero, DIOT, Anexos Transaccionales).
    """

    TIPO_TERCERO_CHOICES = [
        ("CLIENTE", "Cliente"),
        ("PROVEEDOR", "Proveedor"),
        ("EMPLEADO", "Empleado"),
        ("ACCIONISTA", "Accionista"),
        ("GOBIERNO", "Gobierno"),
        ("OTRO", "Otro"),
    ]

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="terceros", db_index=True
    )

    # Identificador fiscal (RUC/Cédula/DNI)
    numero_identificacion = models.CharField(
        max_length=20, help_text="RUC, Cédula, DNI u otro identificador fiscal"
    )

    # Clasificación del tercero
    tipo = models.CharField(max_length=20, choices=TIPO_TERCERO_CHOICES, db_index=True)

    # Datos del tercero
    nombre = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)

    # Control de integridad
    activo = models.BooleanField(default=True, db_index=True)

    # Auditoría
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="terceros_creados", db_constraint=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contabilidad_empresa_tercero"
        verbose_name = "Tercero (Empresa)"
        verbose_name_plural = "Terceros (Empresas)"
        unique_together = ("empresa", "numero_identificacion")
        indexes = [
            models.Index(fields=["empresa", "tipo"]),
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["numero_identificacion"]),
        ]
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.numero_identificacion}) - {self.get_tipo_display()}"

    def clean(self):
        """Validaciones del modelo."""
        super().clean()

        # Validar número de identificación no vacío
        if not self.numero_identificacion or not self.numero_identificacion.strip():
            raise ValidationError(
                {"numero_identificacion": "El número de identificación es obligatorio."}
            )

        # Validar unicidad en la empresa
        existente = (
            EmpresaTercero.objects.filter(
                empresa=self.empresa, numero_identificacion=self.numero_identificacion
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if existente:
            raise ValidationError(
                {"numero_identificacion": "Este identificador ya está registrado en la empresa."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EmpresaAsiento(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="asientos", db_index=True
    )
    numero_asiento = models.PositiveIntegerField(
        editable=False, help_text="Número secuencial del asiento por empresa (auditoría)"
    )
    fecha = models.DateField(db_index=True)
    descripcion_general = models.TextField()
    estado = models.CharField(
        max_length=10, choices=EstadoAsiento.choices, default=EstadoAsiento.BORRADOR, db_index=True
    )
    # Compatibilidad con esquema legado: algunos motores tienen columna 'anulado' NOT NULL
    # que indica si el asiento fue anulado (se mantiene junto con campos de trazabilidad detallada).
    anulado = models.BooleanField(default=False, db_index=True)

    # ===== AUDITORÍA COMPLETA =====
    # Creación
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asientos_creados", db_constraint=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ip_address_creacion = models.GenericIPAddressField(
        null=True, blank=True, help_text="Dirección IP desde la que se creó el asiento"
    )

    # Modificación
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_modificados",
        db_constraint=False
    )
    fecha_modificacion = models.DateTimeField(auto_now=True)
    ip_address_modificacion = models.GenericIPAddressField(
        null=True, blank=True, help_text="Dirección IP desde la que se modificó el asiento"
    )

    # ===== SOFT-DELETE + ANULACIÓN =====
    # Campos para soft-delete y anulación (reversión)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_anulados",
        db_constraint=False
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    ip_address_anulacion = models.GenericIPAddressField(
        null=True, blank=True, help_text="Dirección IP desde la que se anuló el asiento"
    )

    # Asiento de anulación (referencia al contra-asiento)
    anulado_mediante = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="anula_a"
    )

    class Meta:
        db_table = "contabilidad_empresa_asiento"
        verbose_name = "Asiento (Empresa)"
        verbose_name_plural = "Asientos (Empresa)"
        unique_together = ("empresa", "numero_asiento")
        indexes = [
            models.Index(fields=["empresa", "fecha"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "numero_asiento"]),
        ]
        ordering = ["empresa", "-fecha", "-numero_asiento"]

    def __str__(self):
        return f"Asiento #{self.numero_asiento} ({self.empresa.nombre}) - {self.descripcion_general[:40]}"

    def save(self, *args, **kwargs):
        # Asignar número secuencial si es nuevo
        if not self.numero_asiento:
            ultimo = EmpresaAsiento.objects.filter(empresa=self.empresa).aggregate(
                models.Max("numero_asiento")
            )["numero_asiento__max"]
            self.numero_asiento = (ultimo or 0) + 1
        super().save(*args, **kwargs)

    def clean(self):
        """Validaciones de modelo."""
        super().clean()

        # No se puede modificar un asiento confirmado directamente
        if self.pk and self.estado == EstadoAsiento.CONFIRMADO:
            original = EmpresaAsiento.objects.get(pk=self.pk)
            if original.estado == EstadoAsiento.CONFIRMADO:
                raise ValidationError(
                    "No se puede modificar un asiento confirmado. Debe anularlo primero."
                )

        # Un asiento anulado no puede volver a confirmarse
        if self.estado == EstadoAsiento.CONFIRMADO and self.anulado_por:
            raise ValidationError("Un asiento anulado no puede confirmarse.")

    @property
    def esta_balanceado(self):
        """Verifica la partida doble: Debe = Haber."""
        totales = self.lineas.aggregate(
            total_debe=models.Sum("debe"), total_haber=models.Sum("haber")
        )
        debe = totales["total_debe"] or Decimal("0.00")
        haber = totales["total_haber"] or Decimal("0.00")
        return debe == haber

    @property
    def total_debe(self):
        """Suma total del debe."""
        return self.lineas.aggregate(total=models.Sum("debe"))["total"] or Decimal("0.00")

    @property
    def total_haber(self):
        """Suma total del haber."""
        return self.lineas.aggregate(total=models.Sum("haber"))["total"] or Decimal("0.00")

    @property
    def monto_total(self):
        """Monto total del asiento (debe o haber, son iguales si está balanceado)."""
        return self.total_debe

    def anular(self, usuario, motivo):
        """Anula el asiento creando un contra-asiento."""
        from django.db import transaction

        if self.estado != EstadoAsiento.CONFIRMADO:
            raise ValidationError("Solo se pueden anular asientos confirmados.")

        if self.anulado_por:
            raise ValidationError("Este asiento ya está anulado.")

        with transaction.atomic():
            # Crear contra-asiento
            contra_asiento = EmpresaAsiento.objects.create(
                empresa=self.empresa,
                fecha=timezone.now().date(),
                descripcion_general=f"ANULACIÓN: {self.descripcion_general}",
                estado=EstadoAsiento.CONFIRMADO,
                creado_por=usuario,
            )

            # Crear líneas inversas
            for linea in self.lineas.all():
                EmpresaTransaccion.objects.create(
                    asiento=contra_asiento,
                    cuenta=linea.cuenta,
                    detalle_linea=f"Anulación: {linea.detalle_linea or ''}",
                    debe=linea.haber,  # Invertir
                    haber=linea.debe,  # Invertir
                )

            # Marcar como anulado
            self.estado = EstadoAsiento.ANULADO
            self.anulado_por = usuario
            self.fecha_anulacion = timezone.now()
            self.motivo_anulacion = motivo
            self.anulado_mediante = contra_asiento
            self.anulado = True
            self.save()

            return contra_asiento


class EmpresaTransaccion(models.Model):
    asiento = models.ForeignKey(EmpresaAsiento, on_delete=models.CASCADE, related_name="lineas")
    cuenta = models.ForeignKey(
        EmpresaPlanCuenta, on_delete=models.PROTECT, null=True, blank=True, db_index=True
    )

    # Tercero asociado (normalizado)
    tercero = models.ForeignKey(
        EmpresaTercero,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacciones",
        help_text="Cliente, Proveedor, Empleado, etc.",
    )

    detalle_linea = models.CharField(max_length=500, blank=True, null=True)
    debe = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0.00"))
    haber = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0.00"))

    # Auditoría
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transacciones_creadas",
        db_constraint=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "contabilidad_empresa_transaccion"
        verbose_name = "Transacción (Empresa)"
        verbose_name_plural = "Transacciones (Empresa)"
        indexes = [
            models.Index(fields=["asiento", "cuenta"]),
            models.Index(fields=["cuenta"]),
        ]

    def __str__(self):
        return f"Línea Asiento #{self.asiento.numero_asiento} [{self.empresa()}]: {self.cuenta.codigo if self.cuenta else 'N/A'} D:{self.debe} H:{self.haber}"

    def empresa(self):
        return self.asiento.empresa.nombre

    def clean(self):
        """Validaciones de modelo."""
        super().clean()

        # Validar que la cuenta existe y pertenece a la misma empresa
        if self.cuenta and self.asiento:
            if self.cuenta.empresa != self.asiento.empresa:
                raise ValidationError(
                    {"cuenta": "La cuenta debe pertenecer a la misma empresa del asiento."}
                )

            # Validar que solo se usen cuentas auxiliares
            if not self.cuenta.puede_recibir_transacciones:
                raise ValidationError(
                    {
                        "cuenta": f'La cuenta "{self.cuenta.codigo} - {self.cuenta.descripcion}" '
                        f"no es auxiliar. Solo se pueden usar cuentas de último nivel."
                    }
                )

        # Validar que debe y haber no sean ambos > 0
        if self.debe > 0 and self.haber > 0:
            raise ValidationError(
                "Una línea no puede tener valores tanto en debe como en haber. Use líneas separadas."
            )

        # Validar que al menos uno sea > 0
        if self.debe == 0 and self.haber == 0:
            raise ValidationError("Debe o Haber debe ser mayor a cero.")

        # Validar montos negativos
        if self.debe < 0 or self.haber < 0:
            raise ValidationError("Los montos no pueden ser negativos.")

        # Validar naturaleza de la cuenta vs debe/haber (advertencia)
        if self.cuenta:
            if self.cuenta.naturaleza == NaturalezaCuenta.DEUDORA and self.haber > self.debe:
                # Cuenta deudora: es normal que predomine el debe
                pass  # Permitir, pero podríamos agregar warning en el futuro
            elif self.cuenta.naturaleza == NaturalezaCuenta.ACREEDORA and self.debe > self.haber:
                # Cuenta acreedora: es normal que predomine el haber
                pass  # Permitir, pero podríamos agregar warning en el futuro
            # No bloqueamos la operación, solo validamos la lógica básica

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PeriodoContable(models.Model):
    """Modelo para el control de periodos contables (cierre mensual/anual)."""

    class EstadoPeriodo(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"
        BLOQUEADO = "BLOQUEADO", "Bloqueado (Auditoría)"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="periodos")
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField(help_text="Mes del 1-12, o 0 para indicar cierre anual")
    estado = models.CharField(
        max_length=10, choices=EstadoPeriodo.choices, default=EstadoPeriodo.ABIERTO
    )
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="periodos_cerrados",
        db_constraint=False
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, help_text="Observaciones del cierre")

    class Meta:
        db_table = "contabilidad_periodo"
        verbose_name = "Periodo Contable"
        verbose_name_plural = "Periodos Contables"
        unique_together = ("empresa", "anio", "mes")
        indexes = [
            models.Index(fields=["empresa", "anio", "mes"]),
            models.Index(fields=["empresa", "estado"]),
        ]
        ordering = ["-anio", "-mes"]

    def __str__(self):
        mes_str = f"{self.mes:02d}" if self.mes > 0 else "Anual"
        return f"{self.empresa.nombre} - {self.anio}/{mes_str} [{self.estado}]"

    def clean(self):
        """Validaciones del periodo."""
        super().clean()

        # Validar mes
        if self.mes < 0 or self.mes > 12:
            raise ValidationError({"mes": "El mes debe estar entre 0 (anual) y 12."})

        # No se puede cerrar un periodo si hay asientos en borrador
        if self.pk and self.estado == self.EstadoPeriodo.CERRADO:
            borradores_qs = EmpresaAsiento.objects.filter(
                empresa=self.empresa, fecha__year=self.anio, estado=EstadoAsiento.BORRADOR
            )

            # Si mes=0 es cierre anual: evalúa cualquier mes del año; si mes>0 filtra mes concreto
            if self.mes > 0:
                borradores_qs = borradores_qs.filter(fecha__month=self.mes)

            asientos_borrador = borradores_qs.count()

            if asientos_borrador > 0:
                raise ValidationError(
                    f"No se puede cerrar el periodo. Hay {asientos_borrador} asiento(s) en borrador."
                )

    def cerrar(self, usuario):
        """Cierra el periodo contable."""
        if self.estado == self.EstadoPeriodo.CERRADO:
            raise ValidationError("El periodo ya está cerrado.")

        # Validar que no haya borradores
        self.clean()

        self.estado = self.EstadoPeriodo.CERRADO
        self.cerrado_por = usuario
        self.fecha_cierre = timezone.now()
        self.save()

    def reabrir(self, usuario):
        """Reabre el periodo para correcciones (requiere permisos especiales)."""
        if self.estado != self.EstadoPeriodo.CERRADO:
            raise ValidationError("El periodo no está cerrado.")

        if self.estado == self.EstadoPeriodo.BLOQUEADO:
            raise ValidationError("El periodo está bloqueado y no puede reabrirse.")

        self.estado = self.EstadoPeriodo.ABIERTO
        self.notas += f"\n[Reabierto por {usuario.username} el {timezone.now()}]"
        self.save()


class EmpresaSupervisor(models.Model):
    """Relaciona una empresa con un docente que la supervisa (por ejemplo, copia creada desde su plantilla).

    Esto permite que los docentes vean las empresas creadas por estudiantes que provienen
    de sus plantillas o cuyo acceso fue concedido al importar con `join_code`.
    """

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="supervisores")
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supervisiones", db_constraint=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contabilidad_empresa_supervisor"
        verbose_name = "Empresa Supervisor"
        verbose_name_plural = "Empresa Supervisores"
        unique_together = ("empresa", "docente")

    def __str__(self):
        return f"{self.empresa.nombre} supervisada por {self.docente.username}"


class EmpresaComment(models.Model):
    SECTION_CHOICES = [
        ("PL", "Plan de Cuentas"),
        ("DI", "Libro Diario"),
        ("MA", "Libro Mayor"),
        ("BC", "Balance de Comprobación"),
        ("EF", "Estados Financieros"),
        ("KD", "Kardex de Inventario"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="comments")
    section = models.CharField(max_length=2, choices=SECTION_CHOICES)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_constraint=False)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contabilidad_empresa_comment"
        verbose_name = "Comentario (Empresa)"
        verbose_name_plural = "Comentarios (Empresas)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comentario {self.id} en {self.empresa.nombre} - {self.get_section_display()}"


class EmpresaCierrePeriodo(models.Model):
    """Registra los cierres contables de períodos fiscales.

    Un cierre de periodo:
    - Cancela todas las cuentas de resultado (Ingresos, Costos, Gastos)
    - Traslada la utilidad/pérdida a Patrimonio (cuenta Resultados del Ejercicio)
    - Bloquea la edición de asientos en el periodo cerrado
    """

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="cierres_periodo")
    periodo = models.IntegerField(help_text="Año fiscal cerrado (ej: 2025, 2026)")
    fecha_cierre = models.DateField(
        help_text="Fecha en la que se ejecutó el cierre (último día del ejercicio)"
    )
    asiento_cierre = models.ForeignKey(
        "EmpresaAsiento",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cierre_generado",
        help_text="Asiento contable que registra el cierre del periodo",
    )
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Usuario que ejecutó el cierre",
        db_constraint=False
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp de cuando se registró el cierre en el sistema"
    )

    # Resumen financiero del periodo
    utilidad_neta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text="Utilidad o pérdida del ejercicio (Ingresos - Costos - Gastos)",
    )
    total_ingresos = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_costos = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_gastos = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Control
    bloqueado = models.BooleanField(
        default=True, help_text="Si es True, no se permiten crear/editar asientos en este periodo"
    )
    notas = models.TextField(blank=True, help_text="Observaciones sobre el cierre (opcional)")

    class Meta:
        db_table = "contabilidad_empresa_cierre_periodo"
        verbose_name = "Cierre de Periodo"
        verbose_name_plural = "Cierres de Periodos"
        unique_together = ("empresa", "periodo")
        ordering = ["-periodo"]
        indexes = [
            models.Index(fields=["empresa", "-periodo"]),
            models.Index(fields=["fecha_cierre"]),
        ]

    def __str__(self):
        estado = "Bloqueado" if self.bloqueado else "Desbloqueado"
        return f"Cierre {self.periodo} - {self.empresa.nombre} [{estado}]"

    def clean(self):
        """Validaciones del modelo."""
        super().clean()

        # Validar que el periodo sea un año válido
        if self.periodo and (self.periodo < 2000 or self.periodo > 2100):
            raise ValidationError({"periodo": "El periodo debe estar entre 2000 y 2100."})

        # Validar que no exista otro cierre para el mismo periodo en la misma empresa
        if self.pk is None:  # Solo en creación
            if EmpresaCierrePeriodo.objects.filter(
                empresa=self.empresa, periodo=self.periodo
            ).exists():
                raise ValidationError(
                    {
                        "periodo": f"Ya existe un cierre para el periodo {self.periodo} en esta empresa."
                    }
                )


# -------------------------
# Modelos de Control de Inventarios (Kardex)
# -------------------------


class MetodoValoracion(models.TextChoices):
    """Métodos de valoración de inventarios según NIIF."""

    PEPS = "PEPS", "PEPS (Primero en Entrar, Primero en Salir / FIFO)"
    UEPS = "UEPS", "UEPS (Último en Entrar, Primero en Salir / LIFO)"
    PROMEDIO = "PROMEDIO", "Promedio Ponderado"


class TipoMovimientoKardex(models.TextChoices):
    """Tipos de movimientos de inventario."""

    ENTRADA = "ENTRADA", "Entrada (Compra)"
    SALIDA = "SALIDA", "Salida (Venta/Consumo)"
    AJUSTE_ENTRADA = "AJUSTE_ENTRADA", "Ajuste Positivo (Inventario encontrado)"
    AJUSTE_SALIDA = "AJUSTE_SALIDA", "Ajuste Negativo (Merma/Robo)"
    DEVOLUCION_COMPRA = "DEVOLUCION_COMPRA", "Devolución de Compra"
    DEVOLUCION_VENTA = "DEVOLUCION_VENTA", "Devolución de Venta"


class ProductoInventario(models.Model):
    """Maestro de productos para control de inventarios (Kardex).

    Cada producto tiene su propia tarjeta Kardex donde se registran
    todas las entradas y salidas con su valoración.
    """

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="productos_inventario"
    )
    sku = models.CharField(
        max_length=50, db_index=True, help_text="Código único del producto (SKU)"
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # Clasificación
    categoria = models.CharField(
        max_length=100,
        blank=True,
        help_text="Categoría del producto (ej: Electrónica, Alimentos, etc.)",
    )

    # Unidad de medida
    unidad_medida = models.CharField(
        max_length=20, help_text="Unidad de medida (unid, kg, litros, cajas, etc.)"
    )

    # Vinculación contable
    cuenta_inventario = models.ForeignKey(
        EmpresaPlanCuenta,
        on_delete=models.PROTECT,
        related_name="productos",
        help_text="Cuenta contable de inventario (debe ser tipo Activo, ej: 1.1.04)",
    )
    cuenta_costo_venta = models.ForeignKey(
        EmpresaPlanCuenta,
        on_delete=models.PROTECT,
        related_name="productos_costo",
        null=True,
        blank=True,
        help_text="Cuenta de Costo de Ventas (tipo Costo, ej: 5.1)",
    )

    # Método de valoración
    metodo_valoracion = models.CharField(
        max_length=20,
        choices=MetodoValoracion.choices,
        default=MetodoValoracion.PROMEDIO,
        help_text="Método para calcular el costo de las salidas",
    )

    # Control de stock
    stock_minimo = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text="Stock mínimo (alerta de reabastecimiento)",
    )
    stock_maximo = models.DecimalField(
        max_digits=15, decimal_places=3, null=True, blank=True, help_text="Stock máximo (opcional)"
    )

    # Estado
    activo = models.BooleanField(
        default=True, help_text="Si es False, el producto está descontinuado"
    )

    # Auditoría
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="productos_creados",
        db_constraint=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contabilidad_producto_inventario"
        verbose_name = "Producto (Inventario)"
        verbose_name_plural = "Productos (Inventario)"
        unique_together = ("empresa", "sku")
        ordering = ["sku"]
        indexes = [
            models.Index(fields=["empresa", "sku"]),
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["categoria"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.nombre} [{self.empresa.nombre}]"

    def clean(self):
        """Validaciones del modelo."""
        super().clean()

        # Validar que la cuenta de inventario sea tipo Activo
        if self.cuenta_inventario and self.cuenta_inventario.tipo != TipoCuenta.ACTIVO:
            raise ValidationError(
                {"cuenta_inventario": "La cuenta de inventario debe ser de tipo Activo."}
            )

        # Validar que la cuenta de costo sea tipo Costo
        if self.cuenta_costo_venta and self.cuenta_costo_venta.tipo != TipoCuenta.COSTO:
            raise ValidationError(
                {"cuenta_costo_venta": "La cuenta de costo de venta debe ser de tipo Costo."}
            )

        # Validar stock mínimo/máximo
        if self.stock_maximo and self.stock_minimo > self.stock_maximo:
            raise ValidationError(
                {"stock_minimo": "El stock mínimo no puede ser mayor al stock máximo."}
            )

    @property
    def stock_actual(self):
        """Retorna el stock actual consultando el último movimiento Kardex."""
        ultimo = self.movimientos.order_by("-fecha", "-id").first()
        return ultimo.cantidad_saldo if ultimo else Decimal("0.000")

    @property
    def costo_promedio_actual(self):
        """Retorna el costo promedio actual del inventario."""
        ultimo = self.movimientos.order_by("-fecha", "-id").first()
        return ultimo.costo_promedio if ultimo else Decimal("0.00")

    @property
    def valor_inventario_actual(self):
        """Retorna el valor total del inventario (cantidad * costo promedio)."""
        return self.stock_actual * self.costo_promedio_actual

    @property
    def requiere_reabastecimiento(self):
        """True si el stock actual está por debajo del mínimo."""
        return self.stock_actual < self.stock_minimo


class MovimientoKardex(models.Model):
    """Registro de movimientos de inventario (Kardex).

    Cada movimiento representa una entrada o salida de producto,
    calculando automáticamente el nuevo saldo y costo promedio
    según el método de valoración configurado.
    """

    producto = models.ForeignKey(
        ProductoInventario, on_delete=models.PROTECT, related_name="movimientos"
    )
    fecha = models.DateField(db_index=True)
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimientoKardex.choices)

    # Cantidades del movimiento
    cantidad = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text="Cantidad de unidades (positivo para entradas, valor absoluto para salidas)",
    )
    costo_unitario = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        help_text="Costo unitario del movimiento (para entradas) o costo asignado (para salidas)",
    )
    valor_total_movimiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Valor total del movimiento (cantidad * costo_unitario)",
    )

    # Saldos después del movimiento (snapshot)
    cantidad_saldo = models.DecimalField(
        max_digits=15, decimal_places=3, help_text="Stock resultante después del movimiento"
    )
    costo_promedio = models.DecimalField(
        max_digits=15, decimal_places=6, help_text="Costo promedio ponderado después del movimiento"
    )
    valor_total_saldo = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Valor total del inventario después del movimiento (cantidad_saldo * costo_promedio)",
    )

    # Referencia contable
    asiento = models.ForeignKey(
        EmpresaAsiento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_kardex",
        help_text="Asiento contable asociado a este movimiento",
    )

    # Documentos de referencia
    documento_referencia = models.CharField(
        max_length=100, blank=True, help_text="Número de factura, orden de compra, etc."
    )
    tercero = models.ForeignKey(
        EmpresaTercero,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Proveedor (entrada) o cliente (salida)",
    )

    # Observaciones
    observaciones = models.TextField(blank=True)

    # Auditoría
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, db_constraint=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contabilidad_movimiento_kardex"
        verbose_name = "Movimiento Kardex"
        verbose_name_plural = "Movimientos Kardex"
        ordering = ["fecha", "id"]
        indexes = [
            models.Index(fields=["producto", "fecha"]),
            models.Index(fields=["producto", "-fecha", "-id"]),  # Para último movimiento
            models.Index(fields=["tipo_movimiento"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return (
            f"{self.tipo_movimiento} - {self.producto.sku} - "
            f"{self.cantidad} {self.producto.unidad_medida} - {self.fecha}"
        )

    def clean(self):
        """Validaciones del modelo."""
        super().clean()

        # Validar cantidad positiva
        if self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a cero."})

        # Validar costo unitario no negativo
        if self.costo_unitario < 0:
            raise ValidationError({"costo_unitario": "El costo unitario no puede ser negativo."})

        # Validar saldo no negativo (excepto para ajustes)
        if self.cantidad_saldo < 0 and self.tipo_movimiento not in [
            TipoMovimientoKardex.AJUSTE_SALIDA
        ]:
            raise ValidationError(
                {"cantidad_saldo": "El saldo no puede ser negativo. Stock insuficiente."}
            )

    @property
    def es_entrada(self):
        """True si el movimiento incrementa el inventario."""
        return self.tipo_movimiento in [
            TipoMovimientoKardex.ENTRADA,
            TipoMovimientoKardex.AJUSTE_ENTRADA,
            TipoMovimientoKardex.DEVOLUCION_VENTA,
        ]

    @property
    def es_salida(self):
        """True si el movimiento reduce el inventario."""
        return self.tipo_movimiento in [
            TipoMovimientoKardex.SALIDA,
            TipoMovimientoKardex.AJUSTE_SALIDA,
            TipoMovimientoKardex.DEVOLUCION_COMPRA,
        ]


# -------------------------
# Modelos de Análisis e Inteligencia Artificial
# -------------------------


class EmpresaMetrica(models.Model):
    """Almacena métricas financieras calculadas para análisis y dashboards."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="metricas")
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()

    # Métricas de liquidez
    activo_corriente = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    pasivo_corriente = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    razon_corriente = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    prueba_acida = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Métricas de rentabilidad
    ingresos_totales = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    gastos_totales = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    utilidad_neta = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    margen_neto = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    roe = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, help_text="Return on Equity"
    )
    roa = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, help_text="Return on Assets"
    )

    # Métricas de endeudamiento
    total_activos = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_pasivos = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_patrimonio = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    razon_endeudamiento = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )

    # Métricas operacionales
    num_transacciones = models.IntegerField(default=0)
    num_cuentas_activas = models.IntegerField(default=0)

    class Meta:
        db_table = "contabilidad_empresa_metrica"
        verbose_name = "Métrica Empresarial"
        verbose_name_plural = "Métricas Empresariales"
        ordering = ["-fecha_calculo"]
        indexes = [
            models.Index(fields=["empresa", "-fecha_calculo"]),
            models.Index(fields=["periodo_inicio", "periodo_fin"]),
        ]

    def __str__(self):
        return f"Métricas {self.empresa.nombre} - {self.periodo_inicio} a {self.periodo_fin}"


class EmpresaCuentaEmbedding(models.Model):
    """Almacena embeddings vectoriales de cuentas contables para búsqueda semántica y ML."""

    cuenta = models.ForeignKey(
        "EmpresaPlanCuenta", on_delete=models.CASCADE, related_name="embeddings"
    )

    # Embedding como JSON (MariaDB 11.8 soporta VECTOR pero Django ORM no tiene soporte nativo aún)
    # Usaremos raw SQL para insertar/buscar con VECTOR type directamente
    embedding_json = models.JSONField(
        help_text="Representación vectorial de la cuenta (768 dimensiones)"
    )

    # Metadata del embedding
    modelo_usado = models.CharField(
        max_length=100, default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    dimension = models.IntegerField(default=768)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    # Texto usado para generar el embedding
    texto_fuente = models.TextField(
        help_text="Código + Descripción + Tipo usado para generar embedding"
    )

    class Meta:
        db_table = "contabilidad_cuenta_embedding"
        verbose_name = "Embedding de Cuenta"
        verbose_name_plural = "Embeddings de Cuentas"
        indexes = [
            models.Index(fields=["cuenta"]),
            models.Index(fields=["-fecha_generacion"]),
        ]

    def __str__(self):
        return f"Embedding: {self.cuenta.codigo} - {self.cuenta.descripcion[:50]}"


class PrediccionFinanciera(models.Model):
    """Almacena predicciones generadas por modelos ML (Prophet, ARIMA, etc)."""

    TIPO_PREDICCION_CHOICES = [
        ("INGR", "Ingresos"),
        ("GAST", "Gastos"),
        ("FLUJ", "Flujo de Efectivo"),
        ("PATR", "Patrimonio"),
        ("UTIL", "Utilidad"),
    ]

    MODELO_CHOICES = [
        ("PROPHET", "Facebook Prophet"),
        ("ARIMA", "ARIMA"),
        ("LINEAR", "Regresión Lineal"),
        ("RF", "Random Forest"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="predicciones")
    tipo_prediccion = models.CharField(max_length=4, choices=TIPO_PREDICCION_CHOICES)
    modelo_usado = models.CharField(max_length=10, choices=MODELO_CHOICES)

    # Datos de la predicción
    fecha_prediccion = models.DateField(help_text="Fecha para la cual se hace la predicción")
    valor_predicho = models.DecimalField(max_digits=20, decimal_places=2)
    limite_inferior = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intervalo de confianza inferior",
    )
    limite_superior = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intervalo de confianza superior",
    )
    confianza = models.DecimalField(
        max_digits=5, decimal_places=2, default=95.00, help_text="Nivel de confianza en %"
    )

    # Metadata
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    metricas_modelo = models.JSONField(null=True, blank=True, help_text="MAE, RMSE, R², etc.")
    datos_entrenamiento = models.JSONField(
        null=True, blank=True, help_text="Referencia a datos usados"
    )

    class Meta:
        db_table = "contabilidad_prediccion_financiera"
        verbose_name = "Predicción Financiera"
        verbose_name_plural = "Predicciones Financieras"
        ordering = ["fecha_prediccion"]
        indexes = [
            models.Index(fields=["empresa", "tipo_prediccion", "fecha_prediccion"]),
            models.Index(fields=["-fecha_generacion"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_prediccion_display()} - {self.empresa.nombre} ({self.fecha_prediccion}): ${self.valor_predicho}"


class AnomaliaDetectada(models.Model):
    """Registra anomalías detectadas en transacciones mediante ML (Isolation Forest, etc)."""

    TIPO_ANOMALIA_CHOICES = [
        ("MONTO", "Monto Inusual"),
        ("FREQ", "Frecuencia Anormal"),
        ("PTRN", "Patrón Sospechoso"),
        ("CONT", "Inconsistencia Contable"),
        ("TEMP", "Temporal Atípica"),
    ]

    SEVERIDAD_CHOICES = [
        ("BAJA", "Baja"),
        ("MEDIA", "Media"),
        ("ALTA", "Alta"),
        ("CRITICA", "Crítica"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="anomalias")
    asiento = models.ForeignKey(
        EmpresaAsiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="anomalias",
        help_text="Asiento anómalo detectado",
    )
    transaccion = models.ForeignKey(
        EmpresaTransaccion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="anomalias",
        help_text="Transacción anómala detectada",
    )

    tipo_anomalia = models.CharField(max_length=5, choices=TIPO_ANOMALIA_CHOICES)
    severidad = models.CharField(max_length=7, choices=SEVERIDAD_CHOICES, default="MEDIA")

    # Detalles de la anomalía
    score_anomalia = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text="Score del algoritmo (ej: -0.5 en Isolation Forest)",
    )
    descripcion = models.TextField(help_text="Explicación de por qué es anómala")

    # Metadata
    algoritmo_usado = models.CharField(max_length=100, default="IsolationForest")
    fecha_deteccion = models.DateTimeField(auto_now_add=True)

    # Estado
    revisada = models.BooleanField(default=False)
    es_falso_positivo = models.BooleanField(default=False)
    notas_revision = models.TextField(blank=True)
    revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anomalias_revisadas",
        db_constraint=False
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contabilidad_anomalia_detectada"
        verbose_name = "Anomalía Detectada"
        verbose_name_plural = "Anomalías Detectadas"
        ordering = ["-fecha_deteccion", "-severidad"]
        indexes = [
            models.Index(fields=["empresa", "-fecha_deteccion"]),
            models.Index(fields=["severidad", "revisada"]),
            models.Index(fields=["tipo_anomalia"]),
        ]

    def __str__(self):
        return f"Anomalía {self.get_tipo_anomalia_display()} - {self.empresa.nombre} ({self.severidad})"


# -------------------------
# Cache de Métricas para Performance
# -------------------------
class EmpresaMetricasCache(models.Model):
    """
    Cache de métricas pre-calculadas para optimizar el dashboard.
    Se invalida automáticamente con triggers de MariaDB al modificar asientos.
    """

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="metricas_cache")
    periodo = models.DateField(help_text="Primer día del período (YYYY-MM-01)")
    metricas_json = models.JSONField(help_text="Métricas pre-calculadas en formato JSON")
    fecha_calculo = models.DateTimeField(auto_now=True, help_text="Última actualización")

    class Meta:
        db_table = "contabilidad_empresa_metricas_cache"
        verbose_name = "Cache de Métricas"
        verbose_name_plural = "Cache de Métricas"
        unique_together = [("empresa", "periodo")]
        indexes = [
            models.Index(fields=["empresa", "-fecha_calculo"]),
            models.Index(fields=["empresa", "periodo"]),
        ]
        ordering = ["-periodo"]

    def __str__(self):
        return f"Métricas {self.empresa.nombre} - {self.periodo.strftime('%Y-%m')}"
