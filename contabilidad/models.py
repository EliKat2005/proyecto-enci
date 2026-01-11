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
    estado_situacion = models.BooleanField(
        db_comment="True si es cuenta de Balance, False si es de Resultado"
    )
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
        managed = True  # Django ahora gestiona el schema
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
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="empresas"
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
                    estado_situacion=acc.estado_situacion,
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
    estado_situacion = models.BooleanField(
        help_text="True si es cuenta de Balance, False si es de Resultado"
    )
    es_auxiliar = models.BooleanField(
        default=False,
        help_text="True si es una cuenta hoja (auxiliar) que puede recibir transacciones",
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

        # Validar jerarquía: cuentas con hijas no pueden ser auxiliares
        # Evitar acceso a relaciones antes de tener PK
        if self.es_auxiliar and self.pk:
            if self.hijas.exists():
                raise ValidationError(
                    {
                        "es_auxiliar": "Las cuentas que tienen subcuentas no pueden ser marcadas como auxiliares."
                    }
                )

        # No permitir agregar hijas a una cuenta auxiliar
        if self.padre and self.padre.es_auxiliar:
            raise ValidationError(
                {"padre": "No se puede agregar subcuentas a una cuenta auxiliar."}
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
        """Solo las cuentas auxiliares (hojas del árbol) activas pueden recibir transacciones."""
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

    @property
    def estado_label(self):
        """Etiqueta legible para el campo booleano `estado_situacion`.

        True => 'Balance' (Estado de Situación Financiera)
        False => 'Resultado'
        """
        return "Balance" if bool(self.estado_situacion) else "Resultado"


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
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="terceros_creados"
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
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="asientos_creados"
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supervisiones"
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
        ("RP", "Reportes"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="comments")
    section = models.CharField(max_length=2, choices=SECTION_CHOICES)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contabilidad_empresa_comment"
        verbose_name = "Comentario (Empresa)"
        verbose_name_plural = "Comentarios (Empresas)"

    def __str__(self):
        return f"Comentario {self.id} en {self.empresa.nombre} - {self.get_section_display()}"
